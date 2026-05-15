# Data Sources

All data files go under `data/raw/` and are excluded from version control (see `.gitignore`).
This file documents every source, its license, and how to download it.

---

## Administrative boundaries

| Field       | Value |
|-------------|-------|
| File        | `gadm41_ECU_2.shp` |
| Source      | [GADM v4.1](https://gadm.org/download_country.html) |
| Level       | ADM2 (cantones for Ecuador) |
| License     | Free for non-commercial use |
| Download    | https://geodata.ucdavis.edu/gadm/gadm4.1/shp/gadm41_ECU_shp.zip |

---

## Population raster

| Field       | Value |
|-------------|-------|
| File        | `ecu_pop_2025_CN_100m_R2025A_v1.tif` |
| Source      | [WorldPop](https://hub.worldpop.org/) |
| Resolution  | 100m |
| Year        | 2025 |
| License     | CC BY 4.0 |
| Download    | https://hub.worldpop.org/geodata/listing?id=79 |

---

## Relative Wealth Index (RWI)

| Field       | Value |
|-------------|-------|
| File        | `ecu_relative_wealth_index.csv` |
| Source      | [Meta Data for Good](https://data.humdata.org/dataset/relative-wealth-index) |
| Resolution  | ~2.4 km tiles |
| Columns     | `latitude`, `longitude`, `rwi` |
| License     | CC BY 4.0 |
| Download    | https://data.humdata.org/dataset/relative-wealth-index |

---

## Flood hazard maps

| Field       | Value |
|-------------|-------|
| Folder      | `Flood/RP_{rp}/` (one subfolder per return period) |
| Return periods | 10, 20, 50, 75, 100, 200, 500 years |
| Source      | [Fathom Global Flood Maps v3](https://www.fathom.global/) or equivalent open source |
| Format      | GeoTIFF, values in meters of flood depth |
| Notes       | Each subfolder must contain exactly one `.tif` file |

---

## Expected directory layout after download

```
data/
└── raw/
    ├── gadm41_ECU_2.shp         (+ .shx, .dbf, .prj)
    ├── ecu_pop_2025_CN_100m_R2025A_v1.tif
    ├── ecu_relative_wealth_index.csv
    └── Flood/
        ├── RP_10/
        │   └── flood_depth_rp10.tif
        ├── RP_20/
        │   └── flood_depth_rp20.tif
        ├── RP_50/  ...
        ├── RP_75/  ...
        ├── RP_100/ ...
        ├── RP_200/ ...
        └── RP_500/
            └── flood_depth_rp500.tif
```
