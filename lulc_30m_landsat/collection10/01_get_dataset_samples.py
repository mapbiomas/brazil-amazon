"""Landsat Collection 10 stage 1: build scene-level training datasets.

This script assembles stable samples, segments Landsat scenes, propagates
labels through segments, extracts spectral features, and exports one local
GeoJSON dataset per scene.
"""
from pprint import pprint
from utils.helpers import *
import ee
import threading
import datetime
import concurrent.futures
from retry import retry
import time
import sys
import os

sys.path.append(os.path.abspath('.'))


PROJECT = 'ee-mapbiomas-imazon'
# PROJECT = 'mapbiomas'

ee.Authenticate()
ee.Initialize(project=PROJECT)


# Configuration

PATH_DIR = '/home/jailson/Imazon/projects/mapbiomas/mapping_legal_amazon'

# ASSET_ROI = 'projects/imazon-simex/LULC/LEGAL_AMAZON/biomes_legal_amazon'
# ASSET_ROI = 'projects/mapbiomas-workspace/AUXILIAR/biomas-2019'
ASSET_ROI = 'users/jailson/brazilian_legal_amazon'

ASSET_TILES = 'projects/mapbiomas-workspace/AUXILIAR/landsat-mask'

ASSET_LULC = 'projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1'


# this must be your partition raw fc samples
ASSET_SAMPLES_P1 = 'projects/imazon-simex/LULC/COLLECTION9/SAMPLES/mapbiomas_85k_col3_points_w_edge_and_edited_v2_train_LA'
ASSET_SAMPLES_P2 = 'projects/mapbiomas-workspace/VALIDACAO/mapbiomas_85k_col4_points_w_edge_and_edited_v1'

LANDSAT_NEW_NAMES = [
    'blue',
    'green',
    'red',
    'nir',
    'swir1',
    'swir2',
    'pixel_qa',
    'tir'
]

ASSET_LANDSAT_IMAGES = {
    'l5c2': {
        'idCollection': 'LANDSAT/LT05/C02/T1_L2',
        'bandNames': [
            'SR_B1',
            'SR_B2',
            'SR_B3',
            'SR_B4',
            'SR_B5',
            'SR_B7',
            'QA_PIXEL',
            'ST_B6'],
        'newBandNames': LANDSAT_NEW_NAMES,
        'defaultVisParams': {}},
    'l7c2': {
        'idCollection': 'LANDSAT/LE07/C02/T1_L2',
        'bandNames': [
            'SR_B1',
            'SR_B2',
            'SR_B3',
            'SR_B4',
            'SR_B5',
            'SR_B7',
            'QA_PIXEL',
            'ST_B6'],
        'newBandNames': LANDSAT_NEW_NAMES,
    },
    'l8c2': {
        'idCollection': 'LANDSAT/LC08/C02/T1_L2',
                        'bandNames': [
                            'SR_B2',
                            'SR_B3',
                            'SR_B4',
                            'SR_B5',
                            'SR_B6',
                            'SR_B7',
                            'QA_PIXEL',
                            'ST_B10'],
        'newBandNames': LANDSAT_NEW_NAMES,
    },
    'l9c2': {
        'idCollection': 'LANDSAT/LC09/C02/T1_L2',
        'bandNames': [
            'SR_B2',
            'SR_B3',
            'SR_B4',
            'SR_B5',
            'SR_B6',
            'SR_B7',
            'QA_PIXEL',
            'ST_B10'],
        'newBandNames': LANDSAT_NEW_NAMES,
    }}


YEARS = [
    # 1985,
    # 1986, 1987
    # 1988,
    # 1989, 1990, 1991, 1992,
    # 1993, 1994, 1995, 1996,
    # 1997, 1998, 1999, 2000,
    # 2001, 2002, 2003, 2004,
    # 2005, 2006, 2007, 2008,
    # 2009, 2010, 2011, 2012,
    # 2013, 2014,
    # 2015, 2016,
    # 2017, 2018,
    # 2019, 2020,
    # 2021, 2022,
    2023


]


INPUT_FEATURES = [
    'gv',
    'npv',
    'soil',
    'cloud',
    'gvs',
    'ndfi',
    'csfi'
]


# used to calculate stable areas
YEARS_STABLE = [
    # 2000, 2001, 2002, 2003, 2004, 2005,
    # 2006, 2007, 2008, 2009, 2010, 2011,
    2012, 2013, 2014, 2015, 2016, 2017,
    2018, 2019, 2020, 2021, 2022, 2023
]

BANDS_STABLE = list(map(lambda y: f'classification_{str(y)}', YEARS_STABLE))

# Harmonize classes from dataset samples

SAMPLE_REPLACE_VAL = {
    'label': {
        3: 3,
        6: 3,
        5: 3,

        19: 18,
        39: 18,
        20: 18,
        40: 18,
        62: 18,
        41: 18,

        36: 3,

        46: 18,  # coffe
        47: 18,  # citrus
        35: 18,  # palm oil
        48: 18,  # other perennial crops

        9: 3,

        30: 25,
        23: 25,
        22: 25,
        29: 25,
        24: 25,


        15: 15,
        33: 33,

        4: 4,
        12: 12

    }
}

HARMONIZATION_CLASSES_SAMPLES = {
    "AFLORAMENTO ROCHOSO": 25,
    "APICUM": 12,
    "AQUICULTURA": 33,
    "CAMPO ALAGADO E ÁREA PANTANOSA": 11,
    "CANA": 18,
    "FLORESTA INUNDÁVEL": 3,
    "FLORESTA PLANTADA": 3,
    "FORMAÇÃO CAMPESTRE": 12,
    "FORMAÇÃO FLORESTAL": 3,
    "FORMAÇÃO SAVÂNICA": 4,
    "INFRAESTRUTURA URBANA": 25,
    "LAVOURA PERENE": 18,
    "LAVOURA TEMPORÁRIA": 18,
    "MANGUE": 3,
    "MINERAÇÃO": 25,
    "NÃO OBSERVADO": 0,
    "OUTRA FORMAÇÃO NÃO FLORESTAL": 12,
    "OUTRA ÁREA NÃO VEGETADA": 25,
    "PASTAGEM": 15,
    "PRAIA E DUNA": 25,
    "RESTINGA HERBÁCEA": 12,
    "RIO, LAGO E OCEANO": 33,
    "VEGETAÇÃO URBANA": 3
}


EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=30)
MAX_REQUESTS_PER_SECOND = 100

# Input data

roi = ee.FeatureCollection(ASSET_ROI)  # \
# .filter('Bioma == "Amazônia"');

tiles = ee.ImageCollection(ASSET_TILES).filterBounds(roi.geometry())

tiles_list = tiles.reduceColumns(
    ee.Reducer.toList(), ['tile']).get('list').getInfo()

p1 = ee.FeatureCollection(ASSET_SAMPLES_P1)\
    .filterBounds(roi)

p2 = ee.FeatureCollection(ASSET_SAMPLES_P2)\
    .filterBounds(roi)\
    .filter('AMOSTRAS == "Treinamento"')


samples = p1.merge(p2)


'''
    Get Stable Areas
'''


from_vals = [int(x) for x in list(SAMPLE_REPLACE_VAL['label'].keys())]
to_vals = list(SAMPLE_REPLACE_VAL['label'].values())


lulc = ee.Image(ASSET_LULC).select(BANDS_STABLE)

count_runs = lulc.reduce(ee.Reducer.countRuns())

stable = ee.Image(lulc.select(
    'classification_2023').updateMask(count_runs.eq(1)))

stable = ee.Image(stable).remap(from_vals, to_vals, 0).rename('stable')

# Dataset export helpers


@retry()
def get_dataset(image_id: str):
    """Build a GeoDataFrame of training samples for one Landsat scene."""

    # check if file already exists
    if os.path.isfile(
            f'{PATH_DIR}/data/{str(year)}/{tile}/{image_id}.geojson'):
        print(1)
        return None

    image = ee.Image(images.filter(
        f'LANDSAT_SCENE_ID == "{image_id}"').first())

    stable_grid = stable.clip(roi)

    # get segments
    segments = get_segments(ee.Image(image).select(
        ['red', 'green', 'blue', 'swir1', 'swir2']))

    segments = ee.Image(segments).reproject('EPSG:4326', None, 30)

    similar_mask = get_similar_mask(segments, samples_harmonized_tile, 'label')

    if not similar_mask:
        return None

    similar_mask = ee.Image(similar_mask.selfMask())

    # redução de componentes conectados com percentil 5 e 95
    percentil = segments.addBands(stable_grid, ['stable']).reduceConnectedComponents(
        ee.Reducer.percentile([5, 95]), 'segments')

    # redução de componentes conectados com o modo
    validated = segments.addBands(
        stable_grid, ['stable']).reduceConnectedComponents(
        ee.Reducer.mode(), 'segments')

    # multiplica onde os percentis 5 e 95 são iguais a 1
    validated = validated.multiply(
        percentil.select(0).eq(percentil.select(1)).eq(1)
    )

    # similar_mask_validated = similar_mask.mask(similar_mask.eq(validated)).rename('label')
    similar_mask_validated = similar_mask.updateMask(
        similar_mask.eq(validated)).rename('label')

    image = get_fractions(image=image)
    image = get_ndfi(image=image)
    image = get_csfi(image=image)

    # select features
    image = ee.Image(image).select(INPUT_FEATURES +
                                   ['red', 'green', 'blue', 'swir1'])
    # image = ee.Image(image).select(INPUT_FEATURES)

    # get features
    samples_image = image.sampleRegions(
        collection=samples_harmonized_tile,
        scale=30,
        geometries=True
    )

    samples_segments = image.addBands(similar_mask_validated.selfMask()).sample(
        region=roi,
        scale=30,
        numPixels=15,
        # factor=0.003,  # Define o fator de amostragem
        dropNulls=True,
        geometries=True
    )

    # set properties
    # samples_image = samples_image.map(lambda feat: feat.copyProperties(image))
    samples_image = samples_image.map(lambda feat: feat.set(
        'year', year)).filter(ee.Filter.notNull(['.geo']))
    samples_image = samples_image.map(lambda feat: feat.set('tile', tile))

    # samples_segments = samples_segments.map(lambda feat: ee.Feature(feat).copyProperties(image))
    samples_segments = samples_segments.map(
        lambda feat: feat.set(
            'year', year)).filter(
        ee.Filter.notNull(
            ['.geo']))  # .filter(ee.Filter.neq('label', 0))
    samples_segments = samples_segments.map(
        lambda feat: feat.set('tile', tile))

    samples_final = samples_image.merge(samples_segments)

    # convert to geodataframe
    samples_image_gdf = ee.data.computeFeatures({
        'expression': samples_final,
        'fileFormat': 'GEOPANDAS_GEODATAFRAME'
    })

    return samples_image_gdf, image_id


def export_dataset(image_ids: list, year: int, tile: str):
    """Export all available scene datasets for a tile and year."""

    future_to_point = {EXECUTOR.submit(
        get_dataset, image_id): image_id for image_id in image_ids}

    for future in concurrent.futures.as_completed(future_to_point):
        point = future_to_point[future]

        samples_image_gdf = future.result()

        if samples_image_gdf is None:
            print('error - gdf is none')
            continue

        try:
            # export geodataframe
            samples_image_gdf[0].to_file(
                f'{PATH_DIR}/data/{str(year)}/{tile}/{samples_image_gdf[1]}.geojson', driver='GeoJSON'
            )

        except Exception as e:
            print(e)
            continue

# Main iteration


for year in YEARS:

    # harmonization classes for dataset samples
    year_sample = 'CLASS_' + str(year) if year <= 2022 else 'CLASS_2022'

    samples_harmonized = samples.select(year_sample).remap(
        ee.Dictionary(HARMONIZATION_CLASSES_SAMPLES).keys(),
        ee.Dictionary(HARMONIZATION_CLASSES_SAMPLES).values(),
        year_sample
    ).select([year_sample], ['label'])

    for tile in tiles_list:

        print(tile)

        # check if dir exists
        if not os.path.exists(f'{PATH_DIR}/data/{str(year)}/{tile}'):
            os.makedirs(f'{PATH_DIR}/data/{str(year)}/{tile}')
        else:
            continue

        tile_image = ee.Image(tiles.filter(f'tile == {tile}').first())

        roi = tile_image.geometry()

        center = roi.centroid()

        samples_harmonized_tile = samples_harmonized.filterBounds(roi)

        if samples_harmonized_tile.size().getInfo() == 0:
            continue

        # get landsat images by roi
        l5 = (
            ee.ImageCollection(ASSET_LANDSAT_IMAGES['l5c2']['idCollection'])
            .filterBounds(center)
            .filterDate(f'{str(year)}-01-01', f'{str(year)}-12-31')
            .map(lambda image: apply_scale_factors(image))
            .map(lambda image: image.set('sensor', 'l5'))
            .select(
                ASSET_LANDSAT_IMAGES['l5c2']['bandNames'],
                ASSET_LANDSAT_IMAGES['l5c2']['newBandNames'])
            .map(lambda image: remove_cloud(image))

        )

        l7 = (
            ee.ImageCollection(ASSET_LANDSAT_IMAGES['l7c2']['idCollection'])
            .filterBounds(center)
            .filterDate(f'{str(year)}-01-01', f'{str(year)}-12-31')
            .map(lambda image: apply_scale_factors(image))
            .map(lambda image: image.set('sensor', 'l7'))
            .select(
                ASSET_LANDSAT_IMAGES['l7c2']['bandNames'],
                ASSET_LANDSAT_IMAGES['l7c2']['newBandNames'])
            .map(lambda image: remove_cloud(image))

        )

        l8 = (
            ee.ImageCollection(ASSET_LANDSAT_IMAGES['l8c2']['idCollection'])
            .filterBounds(center)
            .filterDate(f'{str(year)}-01-01', f'{str(year)}-12-31')
            .map(lambda image: apply_scale_factors(image))
            .map(lambda image: image.set('sensor', 'l8'))
            .select(
                ASSET_LANDSAT_IMAGES['l8c2']['bandNames'],
                ASSET_LANDSAT_IMAGES['l8c2']['newBandNames'])
            .map(lambda image: remove_cloud(image))

        )

        l9 = (
            ee.ImageCollection(ASSET_LANDSAT_IMAGES['l9c2']['idCollection'])
            .filterBounds(center)
            .filterDate(f'{str(year)}-01-01', f'{str(year)}-12-31')
            .map(lambda image: apply_scale_factors(image))
            .map(lambda image: image.set('sensor', 'l9'))
            .select(
                ASSET_LANDSAT_IMAGES['l9c2']['bandNames'],
                ASSET_LANDSAT_IMAGES['l9c2']['newBandNames'])
            .map(lambda image: remove_cloud(image))

        )

        images = ee.ImageCollection(l5.merge(l7).merge(l8).merge(l9))

        image_list = images.reduceColumns(
            ee.Reducer.toList(), ['LANDSAT_SCENE_ID']).get('list').getInfo()

        print(f'n images {len(image_list)}')

        export_dataset(image_list, year, tile)
