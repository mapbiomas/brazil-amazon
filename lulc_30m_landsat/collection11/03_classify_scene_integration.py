"""Landsat Collection 11 stage 3: integrate scene classifications by year.

This script merges scene-level classifications from several historical asset
sources, derives temporal features per tile and year, trains an integration
classifier, and exports annual integrated products.
"""
from glob import glob
from pprint import pprint
from utils.helpers import *
import random
import geemap
import concurrent.futures
from retry import retry
import geopandas as gpd
import pandas as pd
import datetime
import sys
import os

sys.path.append(os.path.abspath('.'))


# PROJECT = 'sad-deep-learning-274812'
PROJECT = 'mapbiomas'

ee.Initialize(project=PROJECT)


# Configuration

PATH_DIR = '/home/jailson/Imazon/projects/mapbiomas/mapping_legal_amazon'

# ASSET_ROI = 'projects/imazon-simex/LULC/LEGAL_AMAZON/biomes_legal_amazon'
# ASSET_ROI = 'projects/mapbiomas-workspace/AUXILIAR/biomas-2019'
ASSET_ROI = 'users/jailson/brazilian_legal_amazon'

ASSET_TILES = 'projects/mapbiomas-workspace/AUXILIAR/landsat-mask'

# PATH_SAMPLES = 'mapbiomas_classification\\data\\2024'
PATH_SAMPLES = f'{PATH_DIR}/data'

PATH_AREAS = f'{PATH_DIR}/data/area/area_c9_amzlegal.csv'

ASSET_CLASSIFICATION = 'projects/ee-cgi-imazon/assets/mapbiomas/lulc_landsat/classification'

# ASSET_OUTPUT = 'projects/ee-mapbiomas-imazon/assets/mapbiomas/lulc_landsat/integrated'
# ASSET_OUTPUT = 'projects/sad-deep-learning-274812/assets/mapbiomas/lulc_landsat/integrated'
ASSET_OUTPUT = 'projects/ee-cgi-imazon/assets/mapbiomas/lulc_landsat/integrated'

ASSETS_CLS_VERSIONS = {
    'classification_p1': {
        'id': 'projects/imazon-simex/LULC/classification',
        'version': '2'
    },
    'classification_p2': {
        'id': 'projects/imazon-simex/LULC/TEST/classification',
        'version': ''
    },
    'classification_p3': {
        'id': 'projects/imazon-simex/LULC/TEST/classification-2',
        'version': '2'
    },
    'classification_p4': {
        'id': 'projects/imazon-simex/LULC/COLLECTION7/classification',
        'version': '4'
    },
    'classification_p5': {
        'id': 'projects/imazon-simex/LULC/COLLECTION6/classification_review',
        'version': '1'
    },
    'classification_p6': {
        'id': 'projects/imazon-simex/LULC/COLLECTION7/classification_review',
        'version': ''
    },
    'classification_p7': {
        'id': 'projects/imazon-simex/LULC/COLLECTION9/classification',
        'version': ''
    },
    'classification_amz_legal_p1': {
        'id': 'projects/imazon-simex/LULC/LEGAL_AMAZON/classification',
        'version': ''
    },
    'classification_amz_legal_p2': {
        'id': 'projects/ee-cgi-imazon/assets/mapbiomas/lulc_landsat/classification',
        'version': ''
    },
    'classification_amz_legal_p3': {
        'id': 'projects/ee-mapbiomas-imazon/assets/mapbiomas/lulc_landsat/classification',
        'version': ''
    }
}

# Version 1: features from all sensors.
OUTPUT_VERSION = '1'


YEARS = [
    # 1985
    # 1985, 1986, 1987
    # 1988, 1989, 1990, 1991,
    # 1992, 1993, 1994, 1995, 1996,
    # 1997, 1998, 1999,
    # 2000, 2001, 2002,
    # 2003, 2004,
    # 2005, 2006, 2007, 2008,
    # 2009, 2010, 2011, 2012, 2013, 2014,
    # 2015, 2016,
    # 2017, 2018,
    # 2019, 2020,
    # 2021,
    # 2022,
    # 2023
    2024
]

# EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1)

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

FEATURE_SPACE = [
    'distinct_total',
    # 'distinct_year',

    'mode',

    'observations_total',
    'observations_year',

    'occurrence_agriculture_total',
    'occurrence_agriculture_year',

    'occurrence_forest_total',
    'occurrence_forest_year',

    'occurrence_grassland_total',
    'occurrence_grassland_year',

    'occurrence_pasture_total',
    'occurrence_pasture_year',

    'occurrence_savanna_total',
    'occurrence_savanna_year',

    'occurrence_water_total',
    'occurrence_water_year',

    'transitions_total',
    'transitions_year'
]


MODEL_PARAMS = {
    'numberOfTrees': 50,
    # 'variablesPerSplit': 4,
    # 'minLeafPopulation': 25
}

N_SAMPLES = 3000


SAMPLE_PARAMS = pd.DataFrame([
    {'label': 3, 'min_samples': N_SAMPLES * 0.20},
    {'label': 4, 'min_samples': N_SAMPLES * 0.15},
    {'label': 12, 'min_samples': N_SAMPLES * 0.09},
    {'label': 15, 'min_samples': N_SAMPLES * 0.20},
    {'label': 18, 'min_samples': N_SAMPLES * 0.15},
    {'label': 25, 'min_samples': N_SAMPLES * 0.05},
    {'label': 33, 'min_samples': N_SAMPLES * 0.10},
])


SAMPLE_REPLACE_VAL = {
    'label': {
        11: 12
    }
}


# Input data

roi_fc = ee.FeatureCollection(ASSET_ROI)  # .filter('Bioma == "Amazônia"')

tiles = ee.ImageCollection(ASSET_TILES).filter(
    ee.Filter.eq('version', '2')).filterBounds(roi_fc.geometry())

df_areas = pd.read_csv(PATH_AREAS).replace(SAMPLE_REPLACE_VAL)\
    .groupby(by=['tile', 'year', 'label'])['area'].sum().reset_index()


# Integration helpers
def setName(image):
    """Store a short scene identifier used to deduplicate source collections."""
    return image.set('name', ee.String(image.get('system:index')).slice(0, 20))


def setYear(image):
    """Extract the acquisition year from the image date property."""
    return image.set(
        'year',
        ee.Number.parse((ee.String(image.get('date')).split('-').get(0))).int()
    )


def add_tiles_around(image, tiles):
    """Attach neighboring tile ids around the current scene footprint."""
    roi_moving = image.geometry().buffer(1, 1)
    tiles_around = tiles.filter(ee.Filter.eq(
        'version', '2')).filterBounds(roi_moving)
    tiles_around_list = tiles_around.aggregate_array('tile')
    return image.set('tiles_around', tiles_around_list)


def get_classification(geometry):
    """Merge historical classification assets and keep one scene per name."""
    collection1 = ee.ImageCollection(
        ASSETS_CLS_VERSIONS['classification_p1']['id']) .filter(
        ee.Filter.eq(
            "version",
            ASSETS_CLS_VERSIONS['classification_p1']['version'])) .filter(
                ee.Filter.bounds(geometry)) .map(setName) .map(setYear)

    collection2 = ee.ImageCollection(
        ASSETS_CLS_VERSIONS['classification_p2']['id']) .filter(
        ee.Filter.bounds(geometry)) .map(setName) .map(setYear)

    collection3 = ee.ImageCollection(
        ASSETS_CLS_VERSIONS['classification_p3']['id']) .filter(
        ee.Filter.eq(
            "version",
            ASSETS_CLS_VERSIONS['classification_p3']['version'])) .filter(
                ee.Filter.bounds(geometry)) .map(setName)

    collection4 = ee.ImageCollection(
        ASSETS_CLS_VERSIONS['classification_p4']['id']) .filter(
        ee.Filter.eq(
            "version",
            ASSETS_CLS_VERSIONS['classification_p4']['version'])) .filter(
                ee.Filter.bounds(geometry)) .map(setName)

    collection5 = ee.ImageCollection(
        ASSETS_CLS_VERSIONS['classification_p5']['id']) .filter(
        ee.Filter.eq(
            "version",
            ASSETS_CLS_VERSIONS['classification_p5']['version'])) .filter(
                ee.Filter.bounds(geometry)) .map(setName)

    collection6 = ee.ImageCollection(
        ASSETS_CLS_VERSIONS['classification_p6']['id']) .filter(
        ee.Filter.bounds(geometry)) .map(setName)

    collection7 = ee.ImageCollection(
        ASSETS_CLS_VERSIONS['classification_p7']['id']) .filter(
        ee.Filter.bounds(geometry)) .map(setName)

    collection_amz_legal_p1 = ee.ImageCollection(
        ASSETS_CLS_VERSIONS['classification_amz_legal_p1']['id']) .filter(
        ee.Filter.bounds(geometry))

    collection_amz_legal_p2 = ee.ImageCollection(
        ASSETS_CLS_VERSIONS['classification_amz_legal_p2']['id']) .filter(
        ee.Filter.bounds(geometry))

    collection_amz_legal_p3 = ee.ImageCollection(
        ASSETS_CLS_VERSIONS['classification_amz_legal_p3']['id']) .filter(
        ee.Filter.bounds(geometry))

    collection5 = collection5 .filter(ee.Filter.inList(
        "name", collection6.aggregate_array('name')).Not())

    collectionFinal = collection6.merge(collection5)

    collection4 = collection4 .filter(ee.Filter.inList(
        "name", collectionFinal.aggregate_array('name')).Not())

    ###
    collectionFinal = collectionFinal.merge(collection4)

    collection3 = collection3 .filter(ee.Filter.inList(
        "name", collectionFinal.aggregate_array('name')).Not())

    collectionFinal = collectionFinal.merge(collection3)

    collection2 = collection2 .filter(ee.Filter.inList(
        "name", collectionFinal.aggregate_array('name')).Not())

    collectionFinal = collectionFinal.merge(collection2)

    collection1 = collection1 .filter(ee.Filter.inList(
        "name", collectionFinal.aggregate_array('name')).Not())

    collectionFinal = collectionFinal.merge(collection1)

    # data 2023
    collectionFinal = collectionFinal.merge(collection7)\

    collection_amz_legal_p1 = collection_amz_legal_p1 .filter(
        ee.Filter.inList("name", collectionFinal.aggregate_array('name')).Not())

    collectionFinal = collectionFinal.merge(collection_amz_legal_p1)

    collection_amz_legal_p2 = collection_amz_legal_p2 .filter(
        ee.Filter.inList("name", collectionFinal.aggregate_array('name')).Not())

    collectionFinal = collectionFinal.merge(collection_amz_legal_p2)

    collection_amz_legal_p3 = collection_amz_legal_p3 .filter(
        ee.Filter.inList("name", collectionFinal.aggregate_array('name')).Not())

    collectionFinal = collectionFinal.merge(collection_amz_legal_p3)

    # Remap classes
    collectionFinal = collectionFinal.map(
        lambda image: image.where(image.eq(19), 18)
        .where(image.eq(13), 12)
        .where(image.eq(25), 15)
        .selfMask()
    )

    return collectionFinal


def get_balanced_samples(
        balance: pd.DataFrame,
        samples: gpd.GeoDataFrame,
        samples_all,
        year_sample,
        tile):
    """Build a tile-level sample set using area proportions and fallback samples."""

    year_sample = 2023 if year_sample > 2023 else year_sample
    output_sp = []

    # get proportio from target tile
    df_proportion = df_areas.query('year == @year_sample and tile == @tile')
    df_proportion['area_p'] = df_proportion['area'].div(
        df_proportion['area'].sum())
    df_proportion['n_samples'] = df_proportion['area_p'].mul(N_SAMPLES).round()

    for index, row in df_proportion.iterrows():
        label, n_sp = row['label'], int(row['n_samples'])

        if samples is not None and label != 0:
            n_sp_avail = samples.query('label == @label').shape[0]
        else:
            n_sp_avail = 0

        if n_sp_avail > n_sp:
            print('n sp', n_sp, n_sp_avail)
            output_sp.append(samples.query('label == @label').sample(n=n_sp))

    output_sp.append(samples_all.query('label == 33').sample(n=20))
    output_sp.append(samples_all.query('label == 4').sample(n=20))
    output_sp.append(samples_all.query('label == 12').sample(n=20))
    output_sp.append(samples_all.query('label == 3').sample(n=20))
    output_sp.append(samples_all.query('label == 15').sample(n=20))
    output_sp.append(samples_all.query('label == 18').sample(n=20))

    df_output = pd.concat(output_sp)

    print(df_output.head(30))

    return df_output


def get_features(tile, year):
    """Derive temporal consistency metrics used by the integration classifier."""

    tile_image = ee.Image(tiles.filter(
        f'tile == {tile}').filter('version == 2').first())

    roi = tile_image.geometry()

    center = roi.centroid()

    classification_tile = get_classification(center).select(0)

    classification_year = classification_tile.filter(f'year == {year}')

    # get metrics

    #
    n_observations_total = classification_tile\
        .map(lambda image: image.gt(0).unmask(0))\
        .reduce(ee.Reducer.sum())\
        .rename('observations_total')

    n_observations_year = classification_year\
        .map(lambda image: image.gt(0).unmask(0))\
        .reduce(ee.Reducer.sum())\
        .rename('observations_year')

    #
    transitions_total = classification_tile\
        .reduce(ee.Reducer.countRuns())\
        .divide(n_observations_total)\
        .rename('transitions_total')

    transitions_year = classification_year\
        .reduce(ee.Reducer.countRuns())\
        .divide(n_observations_year)\
        .rename('transitions_year')

    #
    distinct_total = classification_tile\
        .reduce(ee.Reducer.countDistinctNonNull())\
        .rename('distinct_total')

    # distinct_year = classification_year\
    #    .reduce(ee.Reducer.countDistinctNonNull())\
    #    .rename('distinct_year')

    # mode
    mode_year = classification_year\
        .reduce(ee.Reducer.mode())\
        .rename('mode')

    forest_total = classification_tile\
        .map(lambda image: image.eq(3))\
        .reduce(ee.Reducer.sum())\
        .divide(n_observations_total)\
        .rename('occurrence_forest_total')

    forest_year = classification_year\
        .map(lambda image: image.eq(3))\
        .reduce(ee.Reducer.sum())\
        .divide(n_observations_year)\
        .rename('occurrence_forest_year')

    # occurrence savanna
    savanna_total = classification_tile\
        .map(lambda image: image.eq(4))\
        .reduce(ee.Reducer.sum())\
        .divide(n_observations_total)\
        .rename('occurrence_savanna_total')

    savanna_year = classification_year\
        .map(lambda image: image.eq(4))\
        .reduce(ee.Reducer.sum())\
        .divide(n_observations_year)\
        .rename('occurrence_savanna_year')

    # occurrence grass
    grassland_total = classification_tile\
        .map(lambda image: image.eq(12))\
        .reduce(ee.Reducer.sum())\
        .divide(n_observations_total)\
        .rename('occurrence_grassland_total')

    grassland_year = classification_year\
        .map(lambda image: image.eq(12))\
        .reduce(ee.Reducer.sum())\
        .divide(n_observations_year)\
        .rename('occurrence_grassland_year')

    # occurrence pasture
    pasture_total = classification_tile\
        .map(lambda image: image.eq(15))\
        .reduce(ee.Reducer.sum())\
        .divide(n_observations_total)\
        .rename('occurrence_pasture_total')

    pasture_year = classification_year\
        .map(lambda image: image.eq(15))\
        .reduce(ee.Reducer.sum())\
        .divide(n_observations_year)\
        .rename('occurrence_pasture_year')

    # occurrence agriculture
    agriculture_total = classification_tile\
        .map(lambda image: image.eq(18))\
        .reduce(ee.Reducer.sum())\
        .divide(n_observations_total)\
        .rename('occurrence_agriculture_total')

    agriculture_year = classification_year\
        .map(lambda image: image.eq(18))\
        .reduce(ee.Reducer.sum())\
        .divide(n_observations_year)\
        .rename('occurrence_agriculture_year')

    # occurrence water year
    water_total = classification_tile\
        .map(lambda image: image.eq(33))\
        .reduce(ee.Reducer.sum())\
        .divide(n_observations_total)\
        .rename('occurrence_water_total')

    water_year = classification_year\
        .map(lambda image: image.eq(33))\
        .reduce(ee.Reducer.sum())\
        .divide(n_observations_year)\
        .rename('occurrence_water_year')

    # image feature space
    image = mode_year\
        .addBands(transitions_year)\
        .addBands(n_observations_year)\
        .addBands(forest_year)\
        .addBands(savanna_year)\
        .addBands(grassland_year)\
        .addBands(pasture_year)\
        .addBands(agriculture_year)\
        .addBands(water_year)\
        .addBands(transitions_total)\
        .addBands(distinct_total)\
        .addBands(n_observations_total)\
        .addBands(forest_total)\
        .addBands(savanna_total)\
        .addBands(grassland_total)\
        .addBands(pasture_total)\
        .addBands(agriculture_total)\
        .addBands(water_total)\
        .mask(tile_image)

    return image, roi


def get_sample_values(samples, tile, tiles, year):
    """Sample the feature stack on all training tiles used for the target export."""

    sample_vals = ee.FeatureCollection([])

    # for t in tiles + [tile]:
    for t in tiles:

        print(f'getting samples from tile {t}')

        image, _ = get_features(str(t), year)

        sp = samples.filter(f'tile == {t}')

        sample_values = image.sampleRegions(
            collection=sp,
            scale=30
        )

        sample_vals = sample_vals.merge(sample_values)

    return sample_vals

# @retry()


def classify_data(tile, year):
    """Train and export the integrated classification for one tile and year."""
    try:
        df_samples = gpd.read_file(f'{PATH_SAMPLES}/{year}/{tile}.geojson')\
            .drop(columns=["SCENE_CENTER_TIME"], errors="ignore")

    except Exception as e:
        print(f'erro no tile {e}')
        print('searching random samples')
        df_samples = None

    samples_balanced = get_balanced_samples(
        balance=SAMPLE_PARAMS,
        samples=df_samples,
        samples_all=df_samples_amazon,
        year_sample=year,
        tile=tile
    )

    # if samples_balanced is None: return None
    if df_samples is None:
        return None

    samples_balanced = samples_balanced[['year', 'label', 'geometry', 'tile']]

    # samples_balanced = df_samples[['year', 'label', 'geometry', 'tile']]

    print(samples_balanced.head(50))

    tiles_of_samples = samples_balanced['tile'].values.tolist()
    tiles_of_samples = list(set(tiles_of_samples))

    # convert to ee features
    try:
        samples = geemap.geopandas_to_ee(samples_balanced)
    except Exception as e:
        print('error at getting samples')
        return None

    image_fs, roi = get_features(tile, year)

    print('number tiles', len(tiles_of_samples))

    sp = get_sample_values(samples, tile, tiles_of_samples, year)

    classifier = ee.Classifier.smileRandomForest(**MODEL_PARAMS)\
        .train(sp, 'label', FEATURE_SPACE)

    classification = ee.Image(image_fs
                              .classify(classifier)
                              .rename(['classification'])
                              .copyProperties(image_fs)
                              .copyProperties(image_fs, ['system:footprint'])
                              .copyProperties(image_fs, ['system:time_start'])
                              )

    # probabilities = ee.Image(probabilities).multiply(100).rename('probabilities')

    classification = classification.toByte()
    classification = classification.set('version', OUTPUT_VERSION)
    classification = classification.set('collection_id', 9.0)
    classification = classification.set('tile', str(tile))
    classification = classification.set('biome', 'AMAZONIA')
    classification = classification.set('territory', 'AMAZONIA')
    classification = classification.set('source', 'Imazon')
    classification = classification.set('year', year)

    name = '{}-{}-{}'.format(int(tile), year, OUTPUT_VERSION)
    assetId = '{}/{}'.format(ASSET_OUTPUT, name)

    region = roi.getInfo()['coordinates']

    print(f'exporting features: {name}')

    try:
        task = ee.batch.Export.image.toAsset(
            image=classification,  # .addBands(probabilities),
            description=name,
            assetId=assetId,
            pyramidingPolicy={".default": "mode"},
            region=region,
            scale=30,
            maxPixels=1e+13
        )

        task.start()
    except Exception as e:
        print(f'erro exporting -  {e}')
        return None

    return f'success exporting tile {tile}'


# Main iteration

# add property
# tiles = tiles.map(lambda image: add_tiles_around(image, tiles))

for year in YEARS:

    tiles_list = tiles\
        .filterBounds(roi_fc.geometry()).sort('tile', False)\
        .reduceColumns(ee.Reducer.toList(), ['tile']).get('list').getInfo()

    tiles_list_loaded = ee.ImageCollection(ASSET_OUTPUT)\
        .filter(f'version == "{OUTPUT_VERSION}" and year == {str(year)}')\
        .reduceColumns(ee.Reducer.toList(), ['tile']).get('list').getInfo()

    tiles_list_target = set(tiles_list) - set(tiles_list_loaded)

    file_samples = []
    for i in glob(f'{PATH_DIR}/data/{year}/*'):
        try:
            file_samples.append(gpd.read_file(i).drop(
                columns=["SCENE_CENTER_TIME"], errors="ignore"))
        except Exception as e:
            print(e)
            continue

    df_samples_amazon = pd.concat(file_samples)

    for tile in tiles_list_target:

        result = classify_data(tile, year)

        if result is None:
            print('error - exporting ')
            continue
