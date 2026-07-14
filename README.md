<div>
    <img src='./lulc_30m_landsat/assets/logo.png' height='auto' width='240' align='right'>
    <h1>Amazon Biome</h1>
</div>

Developed by ***Imazon*** e ***Ecode***.

## About

This repository contains land use and land cover workflows for the **Amazon** biome.

We highly recommend the reading of [Amazon's Appendix of the Algorithm Theoretical Basis Document (ATBD)](https://mapbiomas.org/download-dos-atbds). The fundamental information about the classification and methodology is there.

## Repository Structure

### `lulc_30m_landsat/`
Contains the current 30 m Landsat workflow, including shared modules, Collection 9 scripts, CSV rule tables, and assets.

- [Collection 9 workflow](./lulc_30m_landsat/collection9)
- [Shared Python modules](./lulc_30m_landsat/modules)
- [Support CSV files](./lulc_30m_landsat/csv)
- [Landsat workflow notes](./lulc_30m_landsat/collection9/README.md)

### `lulc_10m_sentinel/`
Contains the 10 m Sentinel-2 workflow and its Collection 3 scripts, data tables, and local documentation.

- [Sentinel workspace](./lulc_10m_sentinel/README.md)
- [Sentinel Collection 3](./lulc_10m_sentinel/collection-3/README.md)
