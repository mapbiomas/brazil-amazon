# Sentinel 10 m Workflow

This directory contains the 10 m Sentinel-2 land use and land cover workflow for the Amazon biome.

## Structure

- `collection-3/`: current operational workflow
- `collection-3/data/`: support tables used by the classification stage

## Execution Model

This pipeline is a sequence of Google Earth Engine scripts run manually, in order. Python scripts use the Earth Engine API locally; JavaScript files are intended for the GEE Code Editor.

- `1-mapbiomas-sentinel-2-extract-stable-samples-1.py`
- `2-mapbiomas-sentinel-2-extract-similarity-mask-1.py`
- `3-mapbiomas-sentinel-2-extract-samples-1.py`
- `4-mapbiomas-sentinel-2-classify-2.py`
- `5-mapbiomas-sentinel-2-temporal-filter-1.js`
- `6-mapbiomas-sentinel-2-visualize.js`

## Notes

The scripts use Sentinel mosaic assets, Earth Engine exports, and annual Google Satellite Embedding inputs. Keep version constants explicit in each script and avoid overwriting prior exported assets when evolving the methodology.
