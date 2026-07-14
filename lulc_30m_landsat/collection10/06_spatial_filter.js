/**
 * Landsat Collection 10 stage 4: spatial filtering.
 *
 * This script applies a majority filter and area-based cleanup to the
 * integrated annual classification, then exports the filtered result.
 * Run it in the Google Earth Engine Code Editor after annual integration.
 */
var palettesMb = require('users/mapbiomas/modules:Palettes.js').get('classification8');

// config
var assetRoi = 'projects/imazon-simex/LULC/LEGAL_AMAZON/biomes_legal_amazon';
var asset = 'projects/imazon-simex/LULC/LEGAL_AMAZON/integrated';
var assetOutput = 'projects/imazon-simex/LULC/LEGAL_AMAZON/integrated-filters';

var version = "1";
var outputVersion = "1";

var years = [
  // 1985
  // 1985, 1986, 1987
  // 1988, 1989, 1990, 1991,
  // 1992, 1993, 1994, 1995, 1996,
  // 1997, 1998, 1999,
  // 2000, 2001, 2002,
  // 2003, 2004,
  // 2005, 2006, 2007, 2008,
  // 2009, 2010, 2011, 2012, 2013, 2014,
  // 2015, 2016, 2017, 2018, 2019, 2020,
  // 2021, 2022,
  2023
];

// input
var roi = ee.FeatureCollection(assetRoi).geometry();
var collection = ee.ImageCollection(asset).select('classification')
  .filter('version == "' + version + '"');

// Filtering helpers
function spatialFilterArea(image, classe) {
  // Replace small noisy objects for one class using the border mode.

  var pixelArea = ee.Image.pixelArea().divide(10000);

  var objectId = image.eq(classe).selfMask().connectedComponents({
    connectedness: ee.Kernel.plus(2),
    maxSize: 256
  });

  var objectSize = objectId.select('labels').connectedPixelCount({
    maxSize: 256,
    eightConnected: false
  });

  var objectArea = objectSize.multiply(pixelArea);
  objectArea = objectArea.lte(3).unmask(0);

  var kernel = ee.Kernel.plus({radius: 1});

  var buffer = image.mask(objectArea.eq(0))
    .focalMax({kernel: kernel, iterations: 1})
    .reproject({scale: 30, crs: 'epsg:4326'})
    .mask(objectArea.eq(1));

  objectId = objectId.mask(objectArea.eq(1)).addBands(buffer, null, true);

  // replace noisy by mode of border
  var replacement = objectId.reduceConnectedComponents({
    reducer: ee.Reducer.mode(),
    labelBand: 'labels',
    maxSize: 256
  });

  var imageFiltered = image.where(objectArea.eq(1), replacement);

  return imageFiltered;
}

function majorityFilter(image) {
  // Apply a simple majority filter using a Manhattan neighborhood.

  var kernel = ee.Kernel.manhattan(1);

  image = image.reduceNeighborhood({
    reducer: ee.Reducer.mode(),
    kernel: kernel
  });

  return image.reproject('epsg:4326', null, 30);
}

var visMb = {
  palette: palettesMb,
  min: 0,
  max: 62
};

// Main iteration
years.forEach(function (year) {
  var image = ee.Image(collection.filter('year == ' + String(year)).mosaic())
    .select('classification');

  var imageFiltered = majorityFilter(image);
  imageFiltered = spatialFilterArea(imageFiltered, 15);
  imageFiltered = spatialFilterArea(imageFiltered, 18);

  imageFiltered = imageFiltered.rename('classification');

  imageFiltered = imageFiltered.byte()
    .set('biome', 'AMAZONIA')
    .set('collection_id', 9.0)
    .set('territory', 'BRAZIL')
    .set('source', 'IMAZON')
    .set('version', outputVersion)
    .set('year', year)
    .set('description', 'versão com filtro espacial majority, e área mínima com moda da borda');

  print(imageFiltered);

  Export.image.toAsset({
    image: imageFiltered,
    description: 'AMAZONIA-' + String(year) + '-' + outputVersion,
    assetId: assetOutput + '/' + 'AMAZONIA-' + String(year) + outputVersion,
    pyramidingPolicy: {'.default': 'mode'},
    region: roi.buffer(1000),
    scale: 30,
    maxPixels: 1e13
  });
});
