/**
 * Sentinel Collection 3 stage 6: visualization in the GEE Code Editor.
 *
 * This script loads Sentinel mosaics and annual classification assets for the
 * configured years and adds them to the Earth Engine map for visual QA.
 *
 * Inputs:
 * - `.../GENERAL/classification-amz` assets filtered by `version`
 * - Sentinel mosaic collections filtered by biome and mosaic version
 *
 * Outputs:
 * - No exported assets; this is a viewer-only script
 *
 * Run this in the Google Earth Engine Code Editor after stage 4, or after
 * stage 5 if you adapt it to inspect filtered outputs instead.
 */
var asset = "projects/mapbiomas-brazil/assets/LAND-COVER-10M/COLLECTION-3/GENERAL/classification-amz";

var assetMosaics = [
    'projects/nexgenmap/MapBiomas2/SENTINEL/mosaics-3',
    'projects/mapbiomas-mosaics/assets/SENTINEL/BRAZIL/mosaics-3'
];

var version = "1";

var years = [
    "2016",
    "2017",
    "2018",
    "2019",
    "2020",
    "2021",
    "2022",
    "2023",
    "2024",
    "2025",
];

var palettes = require('users/mapbiomas/modules:Palettes.js');
var paletteMapBiomas = palettes.get('classification8');

var visMapBiomas = {
    min: 0,
    max: 62,
    palette: paletteMapBiomas,
    format: 'png'
};

var visMosaic = {
    'bands': ['swir1_median', 'nir_median', 'red_median'],
    'gain': [0.08, 0.07, 0.2],
    'gamma': 0.85
};

var collection = ee.ImageCollection(asset);

var mosaics = ee.ImageCollection(assetMosaics[0]).merge(ee.ImageCollection(assetMosaics[1]))
        .filter(ee.Filter.eq('version', '3'))
        .filter(ee.Filter.eq('biome', 'AMAZONIA'));

years.forEach(
    function (year) {
        // Load the yearly classification and matching mosaic for side-by-side QA.

        var classificationYear = collection
            .filter('year == ' + year)
            .filter('version == "' + version + '"');

        var mosaicYear = mosaics
            .filter('year == ' + year);

        Map.addLayer(mosaicYear, visMosaic, 'Mosaic ' + year, false);
        Map.addLayer(classificationYear, visMapBiomas, 'Classification ' + year, true);
    }
);
