# Landsat Collection 10

This directory contains the imported Landsat Collection 10 workflow for the Amazon biome. The code was brought from `cgi-imazon/mapbiomas_classification` and kept close to the original layout so script-local paths and helper imports still make sense.

## Structure

- `01_get_dataset_samples.py`: builds training samples from historical assets and stable classes
- `02_classify_scene.py`: classifies Landsat scenes using the sampled dataset
- `03_classify_scene_integration.py`: integrates scene-level outputs into annual products
- `06_spatial_filter.js`: spatial post-processing in the Earth Engine Code Editor
- `07_temporal_filter.js`: temporal post-processing in the Earth Engine Code Editor
- `utils/helpers.py`: shared Earth Engine helper functions used by the Python scripts
- `data/area/`: reference area tables used by the classification workflow
- `requirements.txt`: dependency list from the source repository

## Execution Model

This workflow is a manual Earth Engine pipeline. Python scripts run locally with the Earth Engine API, while `.js` files are intended for the Google Earth Engine Code Editor.

Recommended order:

1. `01_get_dataset_samples.py`
2. `02_classify_scene.py`
3. `03_classify_scene_integration.py`
4. `06_spatial_filter.js`
5. `07_temporal_filter.js`

## Important Notes

The imported scripts still contain environment-specific constants such as `PATH_DIR`, Earth Engine asset ids, project names, and local file paths from the source repository. Review those values before running anything here.

This workflow uses its own local `utils/` and `data/area/` directories inside `collection10/`. Keep those files alongside the scripts unless you also refactor the path handling.

If you adapt the workflow for this repository, prefer small follow-up changes that normalize configuration and paths rather than large rewrites during import.
