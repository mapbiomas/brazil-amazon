<div>
    <img src='../assets/logo.png' height='auto' width='240' align='right'>
    <h1>Amazon Biome</h1>
</div>

Developed by ***Imazon*** e ***Ecode***.

## About

This directory contains the 30 m Landsat workflow used to classify and filter the **Amazon** biome.

We highly recommend reading the [Amazon Appendix of the Algorithm Theoretical Basis Document (ATBD)](https://mapbiomas.org/download-dos-atbds). It contains the core methodology behind this workflow.

## Scope

Use this directory for Landsat-specific notebooks, scripts, tables, and supporting assets. Repository-wide guidance lives in the root [README](../../README.md).

## Workflow Summary

The Landsat pipeline has three main parts:

1. `mapbiomas-classification-amazon.ipynb`
   Configures the classification workflow, samples, feature space, and export paths.
2. `mapbiomas-classification-mode-rf.py`
   Reduces the per-scene classification collection into yearly outputs.
3. `mapbiomas-classification-filter.py`
   Applies spatial and temporal filtering to reduce isolated noise and inconsistent transitions.

## Requirements

Before running the workflow:

1. Create a Google Earth Engine account and configure local authentication.
2. Use Python 3 with the Earth Engine Python API installed.
3. Run commands either from `lulc_30m_landsat/collection9/` or from the repository root with explicit paths.

## Main Inputs

- Notebook: [mapbiomas-classification-amazon.ipynb](./mapbiomas-classification-amazon.ipynb)
- Area table: [data/areas.csv](./data/areas.csv)
- Excluded-scene list: [data/trash.json](./data/trash.json)
- Temporal filter rules: [../csv/temporal-filter-rules-col6.csv](../csv/temporal-filter-rules-col6.csv)

## How to Run

### 1. Classification

Open the notebook and review the main configuration blocks before running:

- Earth Engine asset paths
- Random Forest parameters
- Feature-space band list
- Sample counts and class balance
- Excluded scenes from `data/trash.json`

```sh
jupyter notebook mapbiomas-classification-amazon.ipynb
```

### 2. Yearly Reduction

Run the yearly reduction script after the classification exports are available.

```sh
python3 mapbiomas-classification-mode-rf.py
```

Review `ASSETS`, `INPUT_VERSION`, `OUTPUT_VERSION`, `CLASS_IDS`, `N_SAMPLES`, and `TRASH` before each new run.

### 3. Spatial and Temporal Filter

Run the filter script after the yearly integrated classifications are available.

```sh
python3 mapbiomas-classification-filter.py
```

Review these settings before running:

- `rulesTable` pointing to the temporal rule CSV
- `filterParams` for the spatial cleanup rules
- input and output asset versions

## Notes

This workflow processes Landsat scenes with Earth Engine and depends on versioned asset paths defined inside each script. When the methodology changes, prefer bumping version constants instead of overwriting existing assets.
