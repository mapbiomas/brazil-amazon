# Sentinel Collection 4

This directory contains the current Sentinel-2 Collection 4 mapping workflow for the Amazon biome.

Repository-wide guidance lives in the root [README](../../README.md).

## Workflow Summary

The pipeline is sequential. Each stage exports Earth Engine assets consumed by the next stage.

1. `1-mapbiomas-sentinel-2-extract-stable-samples-1.py`
2. `2-mapbiomas-sentinel-2-extract-similarity-mask-1.py`
3. `3-mapbiomas-sentinel-2-extract-samples-1.py`
4. `4-mapbiomas-sentinel-2-classify-2.py`
5. `5-mapbiomas-sentinel-2-temporal-filter-1.js`
6. `6-mapbiomas-sentinel-2-visualize.js`

## How to Run

Run Python scripts with an authenticated Earth Engine environment, in numeric order. Run JavaScript files in the Google Earth Engine Code Editor after the classification assets are available.

Example:

```sh
python3 lulc_10m_sentinel/collection-4/1-mapbiomas-sentinel-2-extract-stable-samples-1.py
python3 lulc_10m_sentinel/collection-4/2-mapbiomas-sentinel-2-extract-similarity-mask-1.py
python3 lulc_10m_sentinel/collection-4/3-mapbiomas-sentinel-2-extract-samples-1.py
python3 lulc_10m_sentinel/collection-4/4-mapbiomas-sentinel-2-classify-2.py
```

## Script Reference

### `1-mapbiomas-sentinel-2-extract-stable-samples-1.py`
Builds a stable-reference map from MapBiomas Collection 10 and exports stratified point samples by grid. Inputs: Sentinel mosaic collection, MapBiomas coverage asset, and grid layer. Outputs: `AMAZONIA-STABLE-*` and `POINTS/<grid>-STABLE-*`.

### `2-mapbiomas-sentinel-2-extract-similarity-mask-1.py`
Segments each Sentinel mosaic with SNIC, transfers labels from stable points to segments, validates segment agreement, and exports labeled segment masks. Input points must already exist for the same `N_SAMPLES` and `STABLE_VERSION`.

### `3-mapbiomas-sentinel-2-extract-samples-1.py`
Samples pixels from the segment masks and joins them with Sentinel spectral features plus Google Satellite Embedding annual bands `A00` to `A63`. Outputs training tables to `.../TRAINED`. This stage skips assets that already exist in the target folder.

### `4-mapbiomas-sentinel-2-classify-2.py`
Loads trained samples, trains one Random Forest per grid and year, and exports classification rasters to `.../GENERAL/classification-amz`. Includes a single-class fallback to avoid classifier failure on homogeneous tiles.

### `5-mapbiomas-sentinel-2-temporal-filter-1.js`
Runs in the GEE Code Editor. It merges yearly classifications, applies a natural-class mode rule across years, then removes isolated temporal flips before exporting filtered annual rasters to `classification-amz-ft`.

### `6-mapbiomas-sentinel-2-visualize.js`
Runs in the GEE Code Editor. It overlays the classification collection and Sentinel mosaics for quick visual QA by year.

### `data/areas-sentinel-2.csv`
Reference table of area by `class`, `grid_name`, and `year`. Treat it as support material for analysis and sanity checks, not as the source of truth for exports.

## Operational Notes

The current scripts initialize Earth Engine with `project='mapbiomas-colombia'` while reading and writing assets under `projects/mapbiomas-brazil/...`. This is intentional for billing/quota and should not be changed casually.

Scripts `1` and `2` currently ship with a fixed 5-grid development subset in `GRID_NAMES`, while `3` and `4` default to full grid discovery when `GRID_NAMES = []`. Before a production rerun, verify whether the intended scope is a test subset or the whole biome.

Scripts `3` and `4` assume the annual embedding image exists for every year in `YEARS`. Check `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` coverage before extending the series.

Version constants such as `MOSAIC_VERSION`, `STABLE_VERSION`, `SEGMENTS_VERSION`, `SAMPLES_VERSION`, and `OUTPUT_VERSION` are part of the asset contract between stages. Change them deliberately and keep dependent scripts aligned.
