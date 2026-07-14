<p align="center">
    <img src="./assets/header-banner-v2.png" alt="Imazon and Ecode banner">
</p>

# Amazon Biome

Developed by ***Imazon*** e ***Ecode***.

## About

This repository contains land use and land cover workflows for the **Amazon** biome.

We highly recommend reading the [Amazon Appendix of the Algorithm Theoretical Basis Document (ATBD)](https://mapbiomas.org/download-dos-atbds). It contains the core methodology behind these workflows.

## Getting Started

Use the workflow-specific README inside the directory you plan to work on.

- Start with [lulc_30m_landsat/collection9/README.md](./lulc_30m_landsat/collection9/README.md) for the established Landsat 30 m pipeline.
- Start with [lulc_30m_landsat/collection10/README.md](./lulc_30m_landsat/collection10/README.md) for the imported Landsat Collection 10 pipeline.
- Start with [lulc_10m_sentinel/collection-3/README.md](./lulc_10m_sentinel/collection-3/README.md) for the Sentinel-2 10 m Collection 3 pipeline.
- Use the root README only for repository-wide orientation and directory layout.

## Repository Structure

### `lulc_30m_landsat/`
Contains Landsat workflows and supporting code, including shared modules, Collection 9 scripts, Collection 10 imports, and CSV rule tables.

- [Collection 9 workflow](./lulc_30m_landsat/collection9)
- [Collection 10 workflow](./lulc_30m_landsat/collection10)
- [Shared Python modules](./lulc_30m_landsat/modules)
- [Support CSV files](./lulc_30m_landsat/csv)
- [Landsat workflow notes](./lulc_30m_landsat/collection9/README.md)

### `lulc_10m_sentinel/`
Contains the 10 m Sentinel-2 workflow and its Collection 3 scripts, data tables, and local documentation.

- [Sentinel workspace](./lulc_10m_sentinel/README.md)
- [Sentinel Collection 3](./lulc_10m_sentinel/collection-3/README.md)
