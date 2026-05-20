# GAIA 2.0

An open methodology and platform developed by the **Inter-American Development Bank** for estimating the annual average impact of natural hazards on people, weighted by socioeconomic characteristics.

![version](https://img.shields.io/badge/version-2.0.0-blue)

---

# ✨ Description

The GAIA 2.0 computation engine is implemented in a set of Python modules developed by the Disaster Risk Management Team of the Inter-American Development Bank. The architecture separates the calculation logic from the orchestration layer, facilitating integration with external web platforms and extension to new hazard types and countries.

> Current pilot: **Ecuador, flood hazard.**

## Modules

| Module | Description |
| --- | --- |
| `run_floods_ecuador.py` | Main orchestration script: loads config, runs the 5-step pipeline, and writes outputs |
| `methodology/common/exposure.py` | Shared utilities: population raster → points, Relative Wealth Index (RWI) assignment |
| `methodology/floods/impact.py` | Flood-specific: array-based exposure sampling, AAP calculation, boundary aggregation |
| `config/settings.yaml` | All configurable parameters (return periods, flood threshold) and data paths |

---

# 📁 Repository structure

```
gaia2-platform/
├── run_floods_ecuador.py           # Main script: Ecuador flood analysis
│
├── methodology/
│   ├── common/
│   │   └── exposure.py             # Population raster → points, RWI assignment
│   └── floods/
│       └── impact.py               # Flood-specific exposure sampling and AAP
│
├── config/
│   └── settings.yaml               # All configurable parameters and paths
│
├── data/
│   └── README.md                   # Data sources, licenses, download instructions
│
├── outputs/
│   └── README.md                   # Output schema (column definitions, CRS, format)
│
└── dashboard/
    ├── app.py                      # Plotly Dash web application
    ├── assets/style.css            # Dashboard styles
    ├── requirements.txt            # Dashboard Python dependencies
    ├── render.yaml                 # Render.com deployment config
    ├── Procfile                    # Gunicorn start command
    └── README.md                   # Run locally + deploy instructions
```

---

# 📊 Dashboard

An interactive Plotly Dash web app for visualising flood impact results is included in `dashboard/`.

```bash
cd dashboard
pip install -r requirements.txt
python app.py          # opens at http://127.0.0.1:8050
```

Features: canton choropleth map, disaggregated population scatter, RWI wealth filter,
metric-aware viewport counter, and a per-canton detail panel.
Data files must exist at `outputs/` (tracked via Git LFS — run `git lfs pull` after cloning).

See [`dashboard/README.md`](dashboard/README.md) for deployment instructions (Render.com).

---

# ⚙️ Prerequisites

Python 3.10 or higher with the following packages:

```
geopandas>=0.14
pandas>=2.0
numpy>=1.26
rasterio>=1.3
shapely>=2.0
pyogrio>=0.9
pyproj>=3.6
pyyaml>=6.0
```

Installation:

```bash
git clone https://github.com/your-org/gaia2-platform.git
cd gaia2-platform
pip install -r requirements.txt
```

---

# 🚀 Usage

## Run the analysis

```bash
python run_floods_ecuador.py
# or with a custom config:
python run_floods_ecuador.py --config config/settings.yaml
```

This script executes the full 5-step pipeline using the data configured in `config/settings.yaml`:

1. Loads GADM ADM2 administrative boundaries
2. Converts the WorldPop population raster to a point cloud (~3.5M points for Ecuador)
3. Assigns the Meta Relative Wealth Index (RWI) via nearest-neighbor spatial join
4. Samples flood depth at each population point for each return period
5. Computes the **Annual Average affected Population (AAP)** via trapezoidal integration

Outputs are written to the directory specified in `config/settings.yaml` (`outputs/` by default).

## Input files

| File | Format | Description |
| --- | --- | --- |
| `gadm41_ECU_2.shp` | Shapefile | GADM v4.1 ADM2 administrative boundaries for Ecuador |
| `ecu_pop_*.tif` | GeoTIFF (100m) | WorldPop 2025 population raster |
| `ecu_relative_wealth_index.csv` | CSV (`latitude`, `longitude`, `rwi`) | Meta Relative Wealth Index |
| `Flood/RP_{rp}/Ecuador.tif` | GeoTIFF | Flood depth rasters per return period (m) |

See [`data/README.md`](data/README.md) for download instructions and expected directory layout.

---

# 📖 Module descriptions

## methodology/common/exposure.py

```python
from methodology.common.exposure import raster_to_points, assign_rwi
```

**`raster_to_points(raster_path: str) → GeoDataFrame`**
Converts a GeoTIFF population raster to a point GeoDataFrame. Each valid, positive-population pixel becomes a point at its centroid. Returns a GeoDataFrame with a `population` column and the raster's original CRS.

**`assign_rwi(population_points: GeoDataFrame, rwi_path: str) → GeoDataFrame`**
Assigns the nearest Relative Wealth Index value to each population point via a nearest-neighbor spatial join. Reprojects both datasets to EPSG:3857 for accurate distance computation. Returns the input GeoDataFrame with an added `rwi` column.

## methodology/floods/impact.py

```python
from methodology.floods.impact import sample_flood_exposure, calculate_annual_average, aggregate_to_boundaries
```

**`sample_flood_exposure(population_points, flood_maps_dir, return_periods, threshold=0.1) → GeoDataFrame`**
Samples flood depth at each population point for every return period using array-based raster indexing (`data[rows, cols]`). Pixel row/col indices are computed once and reused across all return periods (which share the same raster grid). Points with depth > `threshold` (m) are marked as exposed. Returns the input GeoDataFrame with added `exposed_{rp}` columns containing the population count if exposed, 0 otherwise.

**`calculate_annual_average(gdf, return_periods, exposed_col_prefix="exposed_", output_col="epop_ave") → GeoDataFrame`**
Computes the Annual Average affected Population (AAP) via vectorized trapezoidal integration over annual exceedance probabilities (AEP = 1/return_period):

```
AAP = AEP_max × E_max − trapezoid(E, AEP)
```

Fully vectorized using NumPy — no row-wise iteration. Returns the GeoDataFrame with an added `epop_ave` column.

**`aggregate_to_boundaries(population_points, boundaries, return_periods) → GeoDataFrame`**
Spatially joins population points to administrative boundary polygons and aggregates exposure. Returns the boundaries GeoDataFrame with added columns:

| Column | Description |
| --- | --- |
| `pop_tot` | Total population within the boundary |
| `epop_{rp}` | Exposed population at each return period |
| `epop_ave` | Annual Average affected Population (AAP) |

---

# 🧑‍💻 Authors

The GAIA 2.0 methodology and computation engine is developed by the **Disaster Risk Management Team** of the **Inter-American Development Bank**.

Development team:
Andrés Abarca, Kenneth Otárola, Ginés Suárez

---

# 📄 License

Copyright© 2025. Banco Interamericano de Desarrollo ("BID"). Uso autorizado [AM-331-A3](LICENSE.md)

## Limitation of Responsibilities

The IDB shall not be responsible, under any circumstance, for damage or indemnification, moral or patrimonial; direct or indirect; accessory or special; or by way of consequence, foreseen or unforeseen, that could arise:

i. Under any theory of liability, whether by contract, intellectual property infringement, negligence, or under any other theory; and/or

ii. As a result of the use of the Digital Tool, including, but not limited to, potential defects in the Digital Tool, or the loss or inaccuracy of data of any kind. This includes costs or damages associated with communication failures and/or computer malfunctions linked to the use of the Digital Tool.
