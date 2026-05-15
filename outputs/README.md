# Output Schema

This file defines the output format produced by the GAIA 2.0 analysis scripts.
Walter uses these outputs to build the public dashboard.

**Any change to column names, format, or CRS must be updated here and communicated to the team.**

---

## ADM2 flood results

**File:** `adm2_flood_results.gpkg`
**Format:** GeoPackage (replaces `.shp` — no 10-character column name limit, single file)
**CRS:** EPSG:4326 (WGS84)
**Geometry:** Polygon (ADM2 administrative boundaries)

### Columns

| Column       | Type    | Description |
|--------------|---------|-------------|
| `GID_2`      | string  | GADM unique identifier for the ADM2 unit |
| `NAME_2`     | string  | Cantón name |
| `NAME_1`     | string  | Province name |
| `pop_tot`    | float   | Total population within the boundary (WorldPop 2025) |
| `epop_10`    | float   | Exposed population at 10-year return period |
| `epop_20`    | float   | Exposed population at 20-year return period |
| `epop_50`    | float   | Exposed population at 50-year return period |
| `epop_75`    | float   | Exposed population at 75-year return period |
| `epop_100`   | float   | Exposed population at 100-year return period |
| `epop_200`   | float   | Exposed population at 200-year return period |
| `epop_500`   | float   | Exposed population at 500-year return period |
| `epop_ave`   | float   | **Annual Average affected Population (AAP)** — primary KPI |
| `geometry`   | polygon | ADM2 boundary polygon |

### Derived columns recommended for the dashboard

These can be computed directly in the dashboard from the columns above:

| Derived metric        | Formula                       | Description |
|-----------------------|-------------------------------|-------------|
| AAP rate (%)          | `epop_ave / pop_tot * 100`    | Share of population affected per year |
| Exposure rate at RP   | `epop_{rp} / pop_tot * 100`   | Share exposed at a given return period |

---

## Population points (flood)

**File:** `population_points_flood.csv`
**Format:** CSV (no geometry — coordinates included as columns)
**Note:** Only rows with `epop_ave > 0` are included.

### Columns

| Column         | Type   | Description |
|----------------|--------|-------------|
| `longitude`    | float  | Point longitude (WGS84) |
| `latitude`     | float  | Point latitude (WGS84) |
| `population`   | float  | Population count at pixel |
| `rwi`          | float  | Relative Wealth Index (Meta, ~2.4km resolution) |
| `exposed_{rp}` | float  | Population value if exposed at RP, else 0 |
| `epop_ave`     | float  | Annual Average affected Population at this point |

---

## Notes on RWI

The Relative Wealth Index is currently assigned to each population point but **not yet used in the AAP calculation**. It is included in the outputs as a basis for future socioeconomic weighting of the impact metric.
