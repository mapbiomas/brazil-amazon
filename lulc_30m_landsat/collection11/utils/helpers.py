"""Shared Earth Engine helpers for the Landsat Collection 10 workflow."""

import ee


def get_fractions(image: ee.image.Image) -> ee.image.Image:
    """Add fraction bands for a Landsat scene image."""

    # default endmembers
    ENDMEMBERS = [
        [0.0119, 0.0475, 0.0169, 0.625, 0.2399, 0.0675],  # GV
        [0.1514, 0.1597, 0.1421, 0.3053, 0.7707, 0.1975],  # NPV
        [0.1799, 0.2479, 0.3158, 0.5437, 0.7707, 0.6646],  # Soil
        [0.4031, 0.8714, 0.79, 0.8989, 0.7002, 0.6607]  # Cloud
    ]

    outBandNames = ['gv', 'npv', 'soil', 'cloud']

    fractions = ee.Image(image).select(
        ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']) .unmix(ENDMEMBERS) .max(0)

    fractions = fractions.rename(outBandNames)

    summed = fractions.expression('b("gv") + b("npv") + b("soil")')

    shade = summed.subtract(1.0).abs().rename("shade")

    fractions = fractions.addBands(shade)

    return image.addBands(fractions)


def get_fractions_mosaic(image: ee.image.Image) -> ee.image.Image:
    """Add fraction bands for a mosaic image with median band names."""

    # default endmembers
    ENDMEMBERS = [
        [0.0119, 0.0475, 0.0169, 0.625, 0.2399, 0.0675],  # GV
        [0.1514, 0.1597, 0.1421, 0.3053, 0.7707, 0.1975],  # NPV
        [0.1799, 0.2479, 0.3158, 0.5437, 0.7707, 0.6646],  # Soil
        [0.4031, 0.8714, 0.79, 0.8989, 0.7002, 0.6607]  # Cloud
    ]

    outBandNames = ['gv', 'npv', 'soil', 'cloud']

    fractions = ee.Image(image).select(['blue_median',
                                        'green_median',
                                        'red_median',
                                        'nir_median',
                                        'swir1_median',
                                        'swir2_median']) .unmix(ENDMEMBERS) .max(0)

    fractions = fractions.rename(outBandNames)

    summed = fractions.expression('b("gv") + b("npv") + b("soil")')

    shade = summed.subtract(1.0).abs().rename("shade")

    fractions = fractions.addBands(shade)

    return ee.Image(image).addBands(fractions)


def get_ndfi(image: ee.image.Image) -> ee.image.Image:
    """Calculate NDFI and add it to image fractions

    Parameters:
        image (ee.Image): Fractions image containing the bands:
        gv, npv, soil, cloud

    Returns:
        ee.Image: Fractions image with NDFI bands
    """
    summed = image.expression('b("gv") + b("npv") + b("soil")')

    gvs = image.select("gv").divide(summed).rename("gvs")

    npv_soil = image.expression('b("npv") + b("soil")')

    ndfi = ee.Image.cat(gvs, npv_soil)\
        .normalizedDifference()\
        .rename('ndfi')

    image = image.addBands(gvs)
    image = image.addBands(ndfi)

    return ee.Image(image)


def get_csfi(image: ee.image.Image) -> ee.image.Image:
    """Calculate CSFI and add it to image fractions

    Parameters:
        image (ee.Image): Fractions image containing the bands:
        gv, npv, soil, cloud

    Returns:
        ee.Image: Fractions image with csfi bands
    """

    csfi = image.expression(
        "(float(b('gv') - b('shade'))/(b('gv') + b('shade')))")

    csfi = csfi.rename(['csfi'])
    # csfi = csfi.multiply(100).add(100).byte().rename(['csfi'])

    image = image.addBands(csfi)

    return ee.Image(image)


def apply_scale_factors(image: ee.image.Image) -> ee.image.Image:
    """Apply Landsat Collection 2 scale factors to optical and thermal bands."""
    optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    thermal_bands = image.select('ST_B.*').multiply(0.00341802).add(149.0)

    return image.addBands(
        optical_bands,
        None,
        True).addBands(
        thermal_bands,
        None,
        True)


def remove_cloud(image: ee.image.Image) -> ee.image.Image:
    """Mask cloud shadow and cloud bits from the Landsat QA band."""
    # Bits 3 and 5 are cloud shadow and cloud, respectively.
    cloudShadowBitMask = 1 << 3
    cloudsBitMask = 1 << 4

    # Get the pixel QA band.
    qa = image.select('pixel_qa')

    # Both flags should be set to zero, indicating clear conditions.
    mask = qa.bitwiseAnd(cloudShadowBitMask).eq(
        0).And(qa.bitwiseAnd(cloudsBitMask).eq(0))

    return image.updateMask(mask).copyProperties(image)


def remove_cloud_s2(
        collection: ee.imagecollection.ImageCollection) -> ee.imagecollection.ImageCollection:
    """Mask Sentinel-2 observations using Cloud Score Plus."""

    CLEAR_THRESHOLD = 0.60

    cloud_prob = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED')

    colFreeCloud = collection.linkCollection(cloud_prob, ['cs'])\
        .map(lambda image:
             image.updateMask(image.select('cs').gte(CLEAR_THRESHOLD))
             .copyProperties(image)
             .copyProperties(image, ['system:footprint'])
             .copyProperties(image, ['system:time_start'])
             )

    return colFreeCloud


def get_segments(image, size=30) -> ee.image.Image:
    """Segment an image into SNIC superpixels."""

    seeds = ee.Algorithms.Image.Segmentation.seedGrid(
        size=size,
        gridType='square'
    )

    snic = ee.Algorithms.Image.Segmentation.SNIC(
        image=image,
        size=size,
        compactness=1,
        connectivity=8,
        neighborhoodSize=2 * size,
        seeds=seeds
    )

    # snic = ee.Image(
    #     snic.copyProperties(ee.Image(image))
    #         .copyProperties(ee.Image(image), ['system:footprint'])
    #         .copyProperties(ee.Image(image), ['system:time_start']))

    snic = ee.Image(snic).copyProperties(ee.Image(image))

    return ee.Image(snic).select(['clusters'], ['segments'])


def get_similar_mask(segments, samples_harmonized, prop):
    """Project sample labels from points onto segment identifiers."""

    samples_segments = segments.sampleRegions(
        collection=samples_harmonized,
        scale=30,
        properties=[prop],
    )

    if samples_segments.size().getInfo() == 0:
        return False

    segments_values = ee.List(
        samples_segments.reduceColumns(ee.Reducer.toList().repeat(2), [
                                       prop, 'segments']).get('list')
    )

    similiar_mask = segments.remap(
        segments_values.get(1),
        segments_values.get(0),
        0
    )

    return similiar_mask.rename([prop])
