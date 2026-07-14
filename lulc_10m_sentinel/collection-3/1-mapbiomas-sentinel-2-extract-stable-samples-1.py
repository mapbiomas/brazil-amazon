"""Sentinel Collection 3 stage 1: extract stable reference samples.

This script builds a stable-reference map from MapBiomas Collection 10
classification bands, remaps classes to the simplified Sentinel workflow
legend, and exports stratified point samples per grid tile.

Inputs:
- Sentinel-2 mosaic collection filtered by biome and mosaic version
- MapBiomas Collection 10 coverage asset
- Grid layer from `projects/mapbiomas-workspace/AUXILIAR/cartas`

Outputs:
- Optional stable raster asset `AMAZONIA-STABLE-*`
- Point assets under `.../SAMPLES/AMAZONIA/POINTS`

Run this before stages 2 to 4. Adjust `GRID_NAMES`, `N_SAMPLES`,
`MOSAIC_VERSION`, and `OUTPUT_VERSION` deliberately because downstream
stages depend on these asset identifiers.
"""
import ee
from pprint import pprint

ee.Initialize(project='mapbiomas-colombia')

ASSET_MOSAICS = 'projects/nexgenmap/MapBiomas2/SENTINEL/mosaics-3'

ASSET_OUTPUT = 'projects/mapbiomas-brazil/assets/LAND-COVER-10M/COLLECTION-3/SAMPLES/AMAZONIA'

ASSET_GRIDS = 'projects/mapbiomas-workspace/AUXILIAR/cartas'

ASSET_MAPBIOMAS = 'projects/mapbiomas-public/assets/brazil/lulc/collection10/mapbiomas_brazil_collection10_coverage_v2'

STABLE_NAME = 'AMAZONIA-STABLE-1'

N_SAMPLES = 1000

YEARS = [
    2016,
    2017,
    2018,
    2019,
    2020,
    2021,
    2022,
    2023,
    2024,
    2025
]

MOSAIC_VERSION = '3'

# versao 1 - amostras sorteadas no mapa estavel
OUTPUT_VERSION = '1'

EXPORT_POINTS = True
EXPORT_MAP = False

GRID_NAMES = [
  "NA-20-V-A",
  "NB-20-Y-C",
  "NB-20-Y-D",
  "SB-18-Z-A",
  "SC-18-X-A"
]

MAPBIOMAS_CLASS_IDS = [
    [3, 3],
    [5, 3],
    [4, 4],
    [12, 12],
    [11, 11],
    [15, 15],
    [18, 18],
    [19, 18],
    [39, 18],
    [20, 18],
    [40, 18],
    [41, 18],
    [36, 18],
    [46, 18],
    [47, 18],
    [48, 18],
    [23, 25],
    [24, 25],
    [25, 25],
    [30, 25],
    [33, 33],
    [31, 33]
]

# Remap Collection 10 classes into the simplified legend used by this workflow.
mapbiomasClassIdsIn = list(
    map(lambda classid: classid[0], MAPBIOMAS_CLASS_IDS))

mapbiomasClassIdsOut = list(
    map(lambda classid: classid[1], MAPBIOMAS_CLASS_IDS))
#
collection = (
    ee.ImageCollection(ASSET_MOSAICS)
    .filter(ee.Filter.eq('version', MOSAIC_VERSION))
    .filter(ee.Filter.eq('biome', 'AMAZONIA'))
)

pprint(collection.size().getInfo())

mapbiomas = ee.Image(ASSET_MAPBIOMAS)

mapbiomas = mapbiomas\
    .select([
        'classification_2016',
        'classification_2017',
        'classification_2018',
        'classification_2019',
        'classification_2020',
        'classification_2021',
        'classification_2022',
        'classification_2023',
        'classification_2024',
    ])

mapbiomas = mapbiomas.bandNames()\
    .iterate(
        lambda band, image:
            ee.Image(image).addBands(
                ee.Image(mapbiomas
                         .select([band])
                         .remap(mapbiomasClassIdsIn, mapbiomasClassIdsOut)
                         .rename([band]))
            ),
        ee.Image().select()
)

mapbiomas = ee.Image(mapbiomas)

# A pixel is stable when its class never changes across the selected years.
stable = (
    mapbiomas
    .select(0)
    .mask(mapbiomas.reduce(ee.Reducer.countRuns())
          .eq(1))
    .rename('stable')
)

if len(GRID_NAMES) == 0:
    GRID_NAMES = collection.aggregate_histogram('grid_name').getInfo().keys()

print(GRID_NAMES)

if EXPORT_MAP:
    task = ee.batch.Export.image.toAsset(
        image=stable,
        description=STABLE_NAME,
        assetId='{}/{}'.format(ASSET_OUTPUT, STABLE_NAME),
        pyramidingPolicy={".default": "mode"},
        region=collection.geometry().bounds(),
        scale=30,
        maxPixels=1e13
    )

    task.start()

if EXPORT_POINTS:
    grids = ee.FeatureCollection(ASSET_GRIDS)

    for gridName in GRID_NAMES:
        grid = grids.filter(ee.Filter.stringContains('grid_name', gridName))

        # Export class-balanced stable points per grid for downstream segmentation.
        samples = stable\
            .stratifiedSample(
                numPoints=0,
                classBand='stable',
                region=grid,
                scale=10,
                classValues=[3, 4, 11, 12, 15, 18, 25, 33],
                classPoints=[N_SAMPLES, N_SAMPLES, N_SAMPLES,
                            N_SAMPLES, N_SAMPLES, N_SAMPLES, N_SAMPLES, N_SAMPLES],
                dropNulls=True,
                geometries=True
            )

        samplesName = '{}-STABLE-{}-{}'.format(gridName, N_SAMPLES, OUTPUT_VERSION)

        task = ee.batch.Export.table.toAsset(
            collection=samples,
            description=samplesName,
            assetId='{}/POINTS/{}'.format(ASSET_OUTPUT, samplesName),
        )

        print('Exporting {}...'.format(samplesName))

        task.start()


"""

"""
