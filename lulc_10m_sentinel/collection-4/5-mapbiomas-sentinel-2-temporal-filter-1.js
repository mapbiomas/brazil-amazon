/**
 * Sentinel Collection 3 stage 5: temporal filtering in the GEE Code Editor.
 *
 * This script loads annual classification assets exported by stage 4, merges
 * them into a time series, applies natural-class mode rules across years, and
 * removes isolated temporal flips before exporting filtered annual rasters.
 *
 * Inputs:
 * - `.../GENERAL/classification-amz` assets for the selected `inputVersion`
 *
 * Outputs:
 * - Filtered assets under `.../GENERAL/classification-amz-ft`
 *
 * Run this in the Google Earth Engine Code Editor after stage 4 has produced
 * all yearly classifications required by `years`.
 */
//
var palette = require('users/mapbiomas/modules:Palettes.js').get('brazil');

//
var assetInput = 'projects/mapbiomas-brazil/assets/LAND-COVER-10M/COLLECTION-3/GENERAL/classification-amz';
var assetOutput = 'projects/mapbiomas-brazil/assets/LAND-COVER-10M/COLLECTION-3/GENERAL/classification-amz-ft';
var assetBiomes = 'projects/mapbiomas-workspace/AUXILIAR/ESTATISTICAS/COLECAO9/biomes-coastal-zone-raster';

//
var inputVersion = '1';
var outputVersion = '11';

var description = 'filtro temporal aplicado sobre o mapa integrado ' + inputVersion.replace('-', '.');

//
var yearVis = 2021;

//
var years = [
    // 2016,
    2017,
    2018,
    2019,
    2020,
    2021,
    2022,
    2023,
    2024,
    2025
];

var region = ee.Geometry.Polygon(
    [[
        [-75.92283687359176, 5.774171194329666],
        [-75.92283687359176, -18.245318048249608],
        [-41.20603999859176, -18.245318048249608],
        [-41.20603999859176, 5.774171194329666]
    ]], null, false
);

//
var biomeIds = {
    'amz': 12,
    // 'caa': 13,
    // 'cer': 14,
    // 'mat': 15,
    // 'pam': 16,
    // 'pan': 17,
};

//
var classesBiome = {
    'amz': [15, 18, 3, 4, 25],
    // 'caa': [3, 22, 25, 29, 12, 49, 50, 4],
    // 'cer': [4, 3, 12, 11, 21, 15, 9, 29, 25],
    // 'mat': [3, 4, 11, 12, 13, 29, 49, 50, 21, 24, 25, 15, 9, 19, 36, 23, 30],
    // 'pam': [25, 9, 3, 50, 11, 29, 30, 24, 21, 18, 23, 49, 12],
    // 'pan': [3, 4, 15],
};

//
var exceptions = {
    'amz': [
        [[3, 15, 18], [3, 15, 18]],
        [[3, 18, 25], [3, 18, 18]],
        [[3, 18, 15], [3, 18, 18]],
        [[33, 15, 3], [33, 3, 3]],
        [[33, 15, 12], [33, 12, 12]],
        [[33, 15, 33], [33, 12, 33]],
        [[4, 18, 25], [4, 18, 18]],
        [[4, 18, 15], [4, 18, 18]],
        // [[33, 15, 11], [33, 12, 11]],
    ],
    // 'caa': [],
    // 'cer': [],
    // 'mat': [
    //     [[3, 21, 41], [3, 21, 41]],
    //     [[3, 21, 39], [3, 21, 39]],
    //     [[3, 21, 20], [3, 21, 20]],
    //     [[33, 3, 11], [33, 11, 11]],
    // ],
    // 'pam': [
    //     // [[25, 3, 21], [25, 21, 21]],
    // ],
    // 'pan': []
};

/**
 * 
 */
var classification = ee.Image(
    years.map(
        function (year) {
            // Each year is loaded as a single-band image for temporal stacking.
            var classificationYear = ee.ImageCollection(assetInput)
                .filter(ee.Filter.eq('version', inputVersion))
                .filter(ee.Filter.eq('year', year))
                .min()
                .rename('classification_' + year.toString());

            var naturalYear = classificationYear.remap([3, 4, 12, 33], [3, 4, 12, 33]).rename('natural_' + year.toString());

            return classificationYear.addBands(naturalYear);
        }
    )
).byte();

// Natural classes are stabilized by their modal class across the whole series.
var naturalMode = classification.select([
    // 'natural_2016',
    'natural_2017',
    'natural_2018',
    'natural_2019',
    'natural_2020',
    'natural_2021',
    'natural_2022',
    'natural_2023',
    'natural_2024',
    'natural_2025'
]).reduce(ee.Reducer.mode());

classification = classification.where(classification.eq(3), naturalMode);
classification = classification.where(classification.eq(4), naturalMode);
classification = classification.where(classification.eq(12), naturalMode);
classification = classification.where(classification.eq(33), naturalMode);

classification = classification.select([
    // 'classification_2016',
    'classification_2017',
    'classification_2018',
    'classification_2019',
    'classification_2020',
    'classification_2021',
    'classification_2022',
    'classification_2023',
    'classification_2024',
    'classification_2025'
]);

print(classification);

//
var biomes = ee.Image(assetBiomes);

// last year to first year
years = years.reverse();

var targetYears = years.slice(1, years.length - 1);

/**
 * Replace temporally isolated pixels for a target class across the series.
 *
 * @param {*} c Class id to be filtered.
 * @param {*} classificationFtd Multi-band classification image being updated.
 * @returns {*} Updated multi-band classification image.
 */
var applyGeneralRules = function (c, classificationFtd) {

    c = ee.Number(c);

    classificationFtd = ee.Image(classificationFtd);

    var tCurrentFtd = ee.List(targetYears).iterate(
        /**
         * Apply the isolated-pixel rule to one target year.
         *
         * @param {*} year Year being updated.
         * @param {*} classificationFtd Current filtered time series image.
         * @returns {*} Updated filtered time series image.
         */
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
            var tCurrentFtd = tCurrent.where(mask.and(tCurrent.eq(c)), tMinus1).rename(bCurrent);

            return classificationFtd.addBands(ee.Image(tCurrentFtd), null, true);

        }, classificationFtd
    );

    return classificationFtd.addBands(ee.Image(tCurrentFtd), null, true);
};

/**
 * Reapply exception kernels that must survive the general temporal filter.
 *
 * @param {*} year Central year of the temporal kernel being evaluated.
 * @param {*} obj Dictionary with filtered image, original image, and exceptions.
 * @returns {*} Updated dictionary with the corrected filtered image.
 */
var applyExceptions = function (year, obj) {

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
        /**
         * Restore an allowed temporal transition pattern for one exception rule.
         *
         * @param {*} exception Exception kernel before/after definition.
         * @param {*} tCurrentFtd Filtered band for the current year.
         * @returns {*} Updated filtered band for the current year.
         */
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
            tCurrentFtd = tCurrentFtd.where(mask.and(tMinus1.eq(cb0).and(tCurrent.eq(cb1)).and(tPlus1.eq(cb2))), ca1);

            return tCurrentFtd;

        }, tCurrentFtd
    );

    // update filtered image
    classificationFtd = classificationFtd.addBands(ee.Image(tCurrentFtd), null, true)

    // update obj
    obj = obj.set('filtered', classificationFtd);

    return obj;
};

/**
 * iterates over biomes and applies rules and exceptions
 */
var filteredBiomes = Object.keys(biomeIds).map(

    function (biomeKey) {

        var classes = classesBiome[biomeKey];
        var biome = biomes.eq(biomeIds[biomeKey]);

        var classificationBiome = classification.mask(biome);

        // apply general rules
        var classificationFtd = ee.List(classes)
            .iterate(
                applyGeneralRules,
                classificationBiome
            );

        // apply exceptions
        var obj = ee.List(targetYears)
            .iterate(
                applyExceptions,
                {
                    'filtered': ee.Image(classificationFtd),
                    'original': classificationBiome,
                    'exceptions': exceptions[biomeKey],
                }
            );

        obj = ee.Dictionary(obj);

        return ee.Image(obj.get('filtered')).copyProperties(classificationBiome);
    }
);

var filtered = ee.ImageCollection.fromImages(ee.List(filteredBiomes)).min();
// print(filtered)

Map.addLayer(classification, {
    'bands': ['classification_' + yearVis.toString()],
    'min': 0,
    'max': 75,
    'palette': palette,
    'format': 'png'
}, 'classification');

Map.addLayer(filtered, {
    'bands': ['classification_' + yearVis.toString()],
    'min': 0,
    'max': 75,
    'palette': palette,
    'format': 'png'
}, 'filtered');

Map.addLayer(filtered.eq(classification).selfMask(), {
    'bands': ['classification_' + yearVis.toString()],
    'min': 0,
    'max': 1,
    'palette': ['#ffffff', '#000000'],
    'format': 'png',
    'opacity': 0.8
}, 'changes');

Map.addLayer(biomes, {
    'min': 1,
    'max': 6,
    'palette': ['#ffffff', '#000000'],
    'format': 'png',
    'opacity': 0.4
}, 'Biomes', false);

/**
  * Export to asset
  */

years.forEach(
    function (year) {

        var filteredYear = filtered
            .select('classification_' + year.toString())
            .set('description', description)
            .set('version', outputVersion)
            .set('territory', 'AMAZONIA')
            .set('source', 'imazon')
            .set('satellite', 'Sentinel-2')
            .set('collection_id', 3.0)
            .set('year', year);

        Export.image.toAsset({
            'image': filteredYear,
            'description': 'AMAZONIA-' + year.toString() + '-' + outputVersion,
            'assetId': assetOutput + '/' + year.toString() + '-' + outputVersion,
            'pyramidingPolicy': {
                ".default": "mode"
            },
            'region': region,
            'scale': 10,
            'maxPixels': 1e13
        });
    }
);


/**
 * 
 */
var Chart = {

    options: {
        'title': 'Inspector',
        'legend': 'none',
        'chartArea': {
            left: 30,
            right: 2,
        },
        'titleTextStyle': {
            color: '#ffffff',
            fontSize: 10,
            bold: true,
            italic: false
        },
        'tooltip': {
            textStyle: {
                fontSize: 10,
            },
            // isHtml: true
        },
        'backgroundColor': '#21242E',
        'pointSize': 6,
        'crosshair': {
            trigger: 'both',
            orientation: 'vertical',
            focused: {
                color: '#dddddd'
            }
        },
        'hAxis': {
            // title: 'Date', //muda isso aqui
            slantedTextAngle: 90,
            slantedText: true,
            textStyle: {
                color: '#ffffff',
                fontSize: 8,
                fontName: 'Arial',
                bold: false,
                italic: false
            },
            titleTextStyle: {
                color: '#ffffff',
                fontSize: 10,
                fontName: 'Arial',
                bold: true,
                italic: false
            },
            viewWindow: {
                max: 7,
                min: 0
            },
            gridlines: {
                color: '#21242E',
                interval: 1
            },
            minorGridlines: {
                color: '#21242E'
            }
        },
        'vAxis': {
            title: 'Class', // muda isso aqui
            textStyle: {
                color: '#ffffff',
                fontSize: 10,
                bold: false,
                italic: false
            },
            titleTextStyle: {
                color: '#ffffff',
                fontSize: 10,
                bold: false,
                italic: false
            },
            viewWindow: {
                max: 62,
                min: 0
            },
            gridlines: {
                color: '#21242E',
                interval: 2
            },
            minorGridlines: {
                color: '#21242E'
            }
        },
        'lineWidth': 0,
        // 'width': '100px',
        'height': '150px',
        // 'margin': '50px 50px 0px 0px',
        'series': {
            0: { color: '#21242E' }
        },

    },

    assets: {
        image: null,
        imagef: null
    },

    data: {
        image: null,
        imagef: null,
        point: null
    },

    legend: {
        0: { 'color': palette[0], 'name': 'Ausência de dados' },
        3: { 'color': palette[3], 'name': 'Formação Florestal' },
        4: { 'color': palette[4], 'name': 'Formação Savânica' },
        5: { 'color': palette[5], 'name': 'Mangue' },
        49: { 'color': palette[49], 'name': 'Restinga Florestal' },
        11: { 'color': palette[11], 'name': 'Área Úmida Natural não Florestal' },
        12: { 'color': palette[12], 'name': 'Formação Campestre' },
        32: { 'color': palette[32], 'name': 'Apicum' },
        29: { 'color': palette[29], 'name': 'Afloramento Rochoso' },
        50: { 'color': palette[50], 'name': 'Restinga Herbácea/Arbustiva' },
        13: { 'color': palette[13], 'name': 'Outra Formação não Florestal' },
        18: { 'color': palette[18], 'name': 'Agricultura' },
        39: { 'color': palette[39], 'name': 'Soja' },
        20: { 'color': palette[20], 'name': 'Cana' },
        40: { 'color': palette[40], 'name': 'Arroz' },
        62: { 'color': palette[62], 'name': 'Algodão' },
        41: { 'color': palette[41], 'name': 'Outras Lavouras Temporárias' },
        46: { 'color': palette[46], 'name': 'Café' },
        47: { 'color': palette[47], 'name': 'Citrus' },
        48: { 'color': palette[48], 'name': 'Outras Lavaouras Perenes' },
        9: { 'color': palette[9], 'name': 'Silvicultura' },
        15: { 'color': palette[15], 'name': 'Pastagem' },
        21: { 'color': palette[21], 'name': 'Mosaico de Usos, Áreas abandonadas' },
        22: { 'color': palette[22], 'name': 'Área não Vegetada' },
        23: { 'color': palette[23], 'name': 'Praia e Duna' },
        24: { 'color': palette[24], 'name': 'Infraestrutura Urbana' },
        30: { 'color': palette[30], 'name': 'Mineração' },
        25: { 'color': palette[25], 'name': 'Outra Área não Vegetada' },
        33: { 'color': palette[33], 'name': 'Rio, Lago e Oceano' },
        31: { 'color': palette[31], 'name': 'Aquicultura' },

    },

    loadData: function () {
        Chart.data.image = classification;
        Chart.data.imagef = filtered;
    },

    init: function () {
        Chart.loadData();
        Chart.ui.init();
    },

    getSamplePoint: function (image, points) {

        var sample = image.sampleRegions({
            'collection': points,
            'scale': 10,
            'geometries': true
        });

        return sample;
    },

    ui: {

        init: function () {

            Chart.ui.form.init();
            Chart.ui.activateMapOnClick();

        },

        activateMapOnClick: function () {

            Map.onClick(
                function (coords) {
                    var point = ee.Geometry.Point(coords.lon, coords.lat);

                    var bandNames = Chart.data.image.bandNames();

                    var newBandNames = bandNames.map(
                        function (bandName) {
                            var name = ee.String(ee.List(ee.String(bandName).split('_')).get(1));

                            return name;
                        }
                    );

                    var image = Chart.data.image.select(bandNames, newBandNames);
                    var imagef = Chart.data.imagef.select(bandNames, newBandNames);

                    Chart.ui.inspect(Chart.ui.form.chartInspectorf, imagef, point, 1.0);
                    Chart.ui.inspect(Chart.ui.form.chartInspector, image, point, 1.0);
                }
            );

            Map.style().set('cursor', 'crosshair');
        },

        refreshGraph: function (chart, sample, opacity) {

            sample.evaluate(
                function (featureCollection) {

                    if (featureCollection !== null) {
                        // print(featureCollection.features);

                        var pixels = featureCollection.features.map(
                            function (features) {
                                return features.properties;
                            }
                        );

                        var bands = Object.getOwnPropertyNames(pixels[0]);

                        // Add class value
                        var dataTable = bands.map(
                            function (band) {
                                var value = pixels.map(
                                    function (pixel) {
                                        return pixel[band];
                                    }
                                );

                                return [band].concat(value);
                            }
                        );

                        // Add point style and tooltip
                        dataTable = dataTable.map(
                            function (point) {
                                var color = Chart.legend[point[1]].color;
                                var name = Chart.legend[point[1]].name;
                                var value = String(point[1]);

                                var style = 'point {size: 4; fill-color: ' + color + '; opacity: ' + opacity + '}';
                                var tooltip = 'year: ' + point[0] + ', class: [' + value + '] ' + name;

                                return point.concat(style).concat(tooltip);
                            }
                        );

                        var headers = [
                            'serie',
                            'id',
                            { 'type': 'string', 'role': 'style' },
                            { 'type': 'string', 'role': 'tooltip' }
                        ];

                        dataTable = [headers].concat(dataTable);

                        chart.setDataTable(dataTable);

                    }
                }
            );
        },

        refreshMap: function () {

            var pointLayer = Map.layers().filter(
                function (layer) {
                    return layer.get('name') === 'Point';
                }
            );

            if (pointLayer.length > 0) {
                Map.remove(pointLayer[0]);
                Map.addLayer(Chart.data.point, { color: 'red' }, 'Point');
            } else {
                Map.addLayer(Chart.data.point, { color: 'red' }, 'Point');
            }

        },

        inspect: function (chart, image, point, opacity) {

            // aqui pode fazer outras coisas além de atualizar o gráfico
            Chart.data.point = Chart.getSamplePoint(image, ee.FeatureCollection(point));

            Chart.ui.refreshMap(Chart.data.point);
            Chart.ui.refreshGraph(chart, Chart.data.point, opacity);

        },

        form: {

            init: function () {

                Chart.ui.form.panelChart.add(Chart.ui.form.chartInspector);
                Chart.ui.form.panelChart.add(Chart.ui.form.chartInspectorf);

                Chart.options.title = 'Integrated';
                Chart.ui.form.chartInspector.setOptions(Chart.options);

                Chart.options.title = 'Integrated - ft';
                Chart.ui.form.chartInspectorf.setOptions(Chart.options);

                // Chart.ui.form.chartInspector.onClick(
                //     function (xValue, yValue, seriesName) {
                //         print(xValue, yValue, seriesName);
                //     }
                // );

                Map.add(Chart.ui.form.panelChart);
            },

            panelChart: ui.Panel({
                'layout': ui.Panel.Layout.flow('vertical'),
                'style': {
                    'width': '250px',
                    // 'height': '200px',
                    'position': 'bottom-right',
                    'margin': '0px 0px 0px 0px',
                    'padding': '0px',
                    'backgroundColor': '#21242E'
                },
            }),

            chartInspector: ui.Chart([
                ['Serie', ''],
                ['', -1000], // número menor que o mínimo para não aparecer no gráfico na inicialização
            ]),

            chartInspectorf: ui.Chart([
                ['Serie', ''],
                ['', -1000], // número menor que o mínimo para não aparecer no gráfico na inicialização
            ])
        }
    }
};

Chart.init();
