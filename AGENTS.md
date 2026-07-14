# Repository Guidelines

## Project Structure & Module Organization
This repository is organized by sensor/product line. `lulc_30m_landsat/` contains the active Landsat workflow: shared logic in `modules/`, operational scripts in `collection9/`, support tables in `csv/`, and static images in `assets/`. `lulc_10m_sentinel/` contains the Sentinel-2 workflow, currently centered on `collection-3/` with numbered Earth Engine scripts and `data/areas-sentinel-2.csv`. Keep root-level docs focused on repository-wide orientation.

## Build, Test, and Development Commands
There is no build system in this repo. Work is run directly with Python 3 and authenticated Earth Engine access.

- `python3 -m pip install earthengine-api jupyter`: install the required local tooling.
- `python3 -m ee authenticate`: authenticate your Earth Engine session before running scripts.
- `jupyter notebook lulc_30m_landsat/collection9/mapbiomas-classification-amazon.ipynb`: open the main Landsat classification workflow.
- `python3 lulc_30m_landsat/collection9/mapbiomas-classification-mode-rf.py`: reduce per-scene classifications into yearly outputs.
- `python3 lulc_30m_landsat/collection9/mapbiomas-classification-filter.py`: apply spatial and temporal cleanup rules.
- `python3 lulc_10m_sentinel/collection-3/1-mapbiomas-sentinel-2-extract-stable-samples-1.py`: start the Sentinel Collection 3 export chain.
- `python3 lulc_10m_sentinel/collection-3/4-mapbiomas-sentinel-2-classify-2.py`: run the Sentinel classification stage after samples are exported.

Run commands from the repository root so relative paths such as `../csv/temporal-filter-rules-col6.csv` resolve correctly.

## Documentation Guidelines
Update the root `README.md` when moving or adding top-level workflows. Keep workflow-specific operational details inside the relevant subdirectory, for example `lulc_30m_landsat/collection9/README.md` and `lulc_10m_sentinel/collection-3/README.md`. Do not mix Landsat and Sentinel execution notes in the same document.

## Coding Style & Naming Conventions
Follow the existing Python style: 4-space indentation, module-level constants in `UPPER_SNAKE_CASE`, functions in `snake_case`, and short descriptive docstrings when behavior is not obvious. Preserve the current Earth Engine pattern of explicit `ee.Initialize()` near script startup. Sentinel scripts also include GEE Code Editor `.js` files; keep them browser/Code Editor compatible and avoid introducing Node-specific syntax.

## Testing Guidelines
This repository does not yet include an automated test suite. Validate changes by running the affected script or notebook path against a known Earth Engine project and checking generated assets, filters, and export targets. If you add tests, prefer `pytest`, place them under `tests/`, and name files `test_<module>.py`.

## Commit & Pull Request Guidelines
Current history uses short, imperative commit messages such as `Update README.md` and `Add files via upload`. Prefer the same style, but make the subject specific, for example `Adjust temporal filter rules for collection 9`. Pull requests should include a brief summary, affected scripts or assets, required Earth Engine datasets, and screenshots or exported examples when notebook outputs change.

## Configuration Tips
Do not hardcode new credentials or private asset IDs in committed files. Keep Earth Engine asset paths, sample lists, and version flags easy to review near the top of each script.
