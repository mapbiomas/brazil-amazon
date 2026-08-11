/**
 * Landsat Collection 10 stage 5: temporal filtering.
 *
 * This script removes isolated temporal changes, applies exception rules, and
 * stabilizes natural-vegetation classes across the selected annual series.
 * Run it in the Google Earth Engine Code Editor after the integrated annual
 * products are available.
 */
var Palettes = require('users/mapbiomas/modules:Palettes.js');
var palette = Palettes.get('classification8');

var asset = 'projects/ee-mapbiomas-imazon/assets/mapbiomas/lulc_landsat/integrated';

var years = [
  2019, 2020, 2021, 2022
];

var classes = [15, 18, 3, 4, 12];

var exceptions = [
  [[3, 15, 18], [3, 15, 18]],
  [[3, 18, 25], [3, 18, 18]],
  [[3, 18, 15], [3, 18, 18]],
  [[33, 15, 3], [33, 3, 3]],
  [[33, 15, 12], [33, 12, 12]],
  [[33, 15, 33], [33, 12, 33]],
  [[4, 18, 25], [4, 18, 18]],
  [[4, 18, 15], [4, 18, 18]],
  [[15, 15, 33], [12, 12, 33]]
];

var targetYears = years.slice(1, years.length - 1);

function applyGeneralRules(c, classificationFtd) {
  // Replace temporally isolated pixels for a target class.

  c = ee.Number(c);

  classificationFtd = ee.Image(classificationFtd);

  var tCurrentFtd = ee.List(targetYears).iterate(
    function (year, classificationFtd) {
      year = ee.Number(year).int();
      classificationFtd = ee.Image(classificationFtd);

      var bMinus1 = ee.String('classification_').cat(ee.String(year.subtract(1)));
      var bCurrent = ee.String('classification_').cat(ee.String(year));
      var bPlus1 = ee.String('classification_').cat(ee.String(year.add(1)));

      var tMinus1 = classificationFtd.select(bMinus1);
      var tCurrent = classificationFtd.select(bCurrent);
      var tPlus1 = classificationFtd.select(bPlus1);

      // temporally isolated pixel mask
      var mask = tCurrent.neq(tMinus1).and(tCurrent.neq(tPlus1));

      // replaced by tMinus1
      var tCurrentFtd = tCurrent.where(
        mask.and(tCurrent.eq(c)),
        tMinus1
      ).rename(bCurrent);

      return classificationFtd.addBands(ee.Image(tCurrentFtd), null, true);
    },
    classificationFtd
  );

  return classificationFtd.addBands(ee.Image(tCurrentFtd), null, true);
}

function applyExceptions(year, obj) {
  // Restore temporal patterns that must survive the generic rule set.

  year = ee.Number(year).int();
  obj = ee.Dictionary(obj);

  var classificationFtd = ee.Image(obj.get('filtered'));
  var classificationOri = ee.Image(obj.get('original'));
  var exceptions = ee.List(obj.get('exceptions'));

  var bMinus1 = ee.String('classification_').cat(ee.String(year.subtract(1)));
  var bCurrent = ee.String('classification_').cat(ee.String(year));
  var bPlus1 = ee.String('classification_').cat(ee.String(year.add(1)));

  var tMinus1 = classificationOri.select(bMinus1);
  var tCurrent = classificationOri.select(bCurrent);
  var tPlus1 = classificationOri.select(bPlus1);

  var tCurrentFtd = classificationFtd.select(bCurrent);

  // temporally isolated pixel mask
  var mask = tCurrent.neq(tMinus1).and(tCurrent.neq(tPlus1));

  // iterate over exceptions list and apply the filter function
  tCurrentFtd = exceptions.iterate(
    function (exception, tCurrentFtd) {
      tCurrentFtd = ee.Image(tCurrentFtd);

      var kernelBef = ee.List(ee.List(exception).get(0));
      var kernelAft = ee.List(ee.List(exception).get(1));

      // cb - class before, ca - class after
      var cb0 = ee.Number(kernelBef.get(0));
      var cb1 = ee.Number(kernelBef.get(1));
      var cb2 = ee.Number(kernelBef.get(2));
      // var ca0 = ee.Number(kernelAft.get(0));
      var ca1 = ee.Number(kernelAft.get(1));
      // var ca2 = ee.Number(kernelAft.get(2));

      // uses tCurrent.eq(cb1) to ignore the changes in tCurrentFtd
      tCurrentFtd = tCurrentFtd.where(
        mask.and(tMinus1.eq(cb0).and(tCurrent.eq(cb1)).and(tPlus1.eq(cb2))),
        ca1
      );

      return tCurrentFtd;
    },
    tCurrentFtd
  );

  // update filtered image
  classificationFtd = classificationFtd.addBands(ee.Image(tCurrentFtd), null, true);

  // update obj
  obj = obj.set('filtered', classificationFtd);

  return obj;
}

function naturalVegetationFilter(image, classIds) {
  // Replace natural-vegetation classes by their temporal mode.

  var bandNames = image.bandNames();

  // mask classIds pixels
  var imageList = bandNames.map(function (bandName) {
    return image.remap(classIds, classIds, null, bandName);
  });

  // reduce to temporal mode
  var temporalMode = ee.ImageCollection.fromImages(imageList).reduce(ee.Reducer.mode());

  temporalMode = ee.Image(temporalMode);

  // replace classIds pixels for temporal mode pixel value
  imageList = bandNames.map(function (band) {
    image = image.select([ee.String(band)]).where(
      image.remap(classIds, ee.List.repeat(1, classIds.length), 0, band),
      temporalMode
    );

    return image;
  });

  image = ee.ImageCollection.fromImages(imageList).toBands();

  return image.rename(bandNames);
}

// Build a multiband annual time series for temporal filtering.
var classificationCollection = ee.ImageCollection(asset);

// convert it to image multi-bands
var classification = ee.Image(
  years.map(function (year) {
    var classificationYear = classificationCollection
      .filter(ee.Filter.eq('year', year))
      .min()
      .rename('classification_' + year.toString());
    return classificationYear;
  })
).byte();

var classificationStable = naturalVegetationFilter(classification, [3, 4, 12]);

// apply general rules
var classificationFtd = ee.List(classes)
  .iterate(
    applyGeneralRules,
    classification
  );

// apply exceptions
var obj = ee.List(targetYears)
  .iterate(
    applyExceptions,
    {
      'filtered': ee.Image(classificationFtd),
      'original': classification,
      'exceptions': exceptions,
    }
  );

obj = ee.Dictionary(obj);

var classificationFiltered = ee.Image(obj.get('filtered')).copyProperties(classification);

years.forEach(function (year) {
  var image = ee.Image(classificationFiltered).select('classification_' + year.toString());
  var imageOrg = ee.Image(classification).select('classification_' + year.toString());
  var imageStable = ee.Image(classificationStable).select('classification_' + year.toString());

  // Map.addLayer(imageOrg, {min: 0, max: 62, palette: palette}, year.toString() + ' - orig', false)
  Map.addLayer(imageStable, {min: 0, max: 62, palette: palette}, year.toString() + ' - stable', false);
  Map.addLayer(image, {min: 0, max: 62, palette: palette}, year.toString() + ' - adj', false);
});
