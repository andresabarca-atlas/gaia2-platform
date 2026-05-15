"""
GAIA 2.0 — Flood impact module
================================
Flood-specific exposure sampling and Annual Average Population (AAP) calculation.

The AAP is computed by integrating the exposed population curve over annual
exceedance probabilities (AEP = 1/return_period) using the trapezoidal rule:

    AAP = AEP_max * E_max - trapz(E, AEP)

where E is the exposed population at each return period and AEP_max corresponds
to the longest return period (lowest frequency event).
"""

import os
import numpy as np
import geopandas as gpd
import rasterio


def sample_flood_exposure(
    population_points: gpd.GeoDataFrame,
    flood_maps_dir: str,
    return_periods: list,
    threshold: float = 0.1,
) -> gpd.GeoDataFrame:
    """
    For each return period, sample flood depth at each population point.
    Points with depth > threshold are considered exposed.

    Parameters
    ----------
    population_points : GeoDataFrame
        Must have a 'population' column and point geometry.
    flood_maps_dir : str
        Directory containing subfolders RP_10, RP_20, ..., each with a .tif raster.
    return_periods : list of int
        Return periods to process (e.g. [10, 20, 50, 75, 100, 200, 500]).
    threshold : float
        Minimum flood depth (m) to consider a point as exposed. Default: 0.1.

    Returns
    -------
    GeoDataFrame — population_points with added columns 'exposed_{rp}' for each RP.
        Value is the population count if exposed, 0 otherwise.
    """
    points = population_points.copy()
    coords = [(p.x, p.y) for p in points.geometry]

    for rp in return_periods:
        raster_path = _find_raster(flood_maps_dir, rp)
        with rasterio.open(raster_path) as src:
            depths = np.array([v[0] for v in src.sample(coords)])
        points[f"exposed_{rp}"] = np.where(depths > threshold, points["population"], 0.0)

    return points


def calculate_annual_average(
    gdf: gpd.GeoDataFrame,
    return_periods: list,
    exposed_col_prefix: str = "exposed_",
    output_col: str = "epop_ave",
) -> gpd.GeoDataFrame:
    """
    Compute Annual Average affected Population (AAP) via vectorized
    trapezoidal integration over exceedance probabilities.

    This is a fully vectorized replacement for the row-wise .apply() approach,
    significantly faster on large datasets.

    Parameters
    ----------
    gdf : GeoDataFrame
        Must contain columns '{exposed_col_prefix}{rp}' for each rp in return_periods.
    return_periods : list of int
        Must be sorted in ascending order (shortest to longest RP).
    exposed_col_prefix : str
        Prefix of the exposure columns. Default: 'exposed_'.
    output_col : str
        Name of the output AAP column. Default: 'epop_ave'.

    Returns
    -------
    GeoDataFrame with added '{output_col}' column.
    """
    poes = 1.0 / np.array(return_periods, dtype=float)  # annual exceedance probabilities
    cols = [f"{exposed_col_prefix}{rp}" for rp in return_periods]

    # Shape: (n_rows, n_return_periods)
    vals = gdf[cols].fillna(0.0).to_numpy()

    # Vectorized trapezoidal integration across return periods (axis=1)
    aap = poes[-1] * vals[:, -1] - np.trapz(vals, poes, axis=1)

    result = gdf.copy()
    result[output_col] = aap
    return result


def aggregate_to_boundaries(
    population_points: gpd.GeoDataFrame,
    boundaries: gpd.GeoDataFrame,
    return_periods: list,
) -> gpd.GeoDataFrame:
    """
    Aggregate point-level flood exposure to administrative boundary polygons.

    Produces one row per boundary with:
      - pop_tot      : total population within the boundary
      - epop_{rp}    : exposed population at each return period
      - epop_ave     : Annual Average affected Population (AAP)

    Parameters
    ----------
    population_points : GeoDataFrame
        Must have 'population' and 'exposed_{rp}' columns for each RP.
    boundaries : GeoDataFrame
        Administrative boundary polygons.
    return_periods : list of int

    Returns
    -------
    GeoDataFrame — boundaries with added exposure columns.
    """
    joined = gpd.sjoin(population_points, boundaries, how="inner", predicate="within")

    result = boundaries.copy()

    # Total population
    pop_sum = (
        joined.groupby(joined.index_right)["population"]
        .sum()
        .rename("pop_tot")
    )
    result = result.join(pop_sum).fillna({"pop_tot": 0.0})

    # Exposed population per return period
    for rp in return_periods:
        col = f"exposed_{rp}"
        out_col = f"epop_{rp}"
        exp_sum = joined.groupby(joined.index_right)[col].sum().rename(out_col)
        result = result.join(exp_sum).fillna({out_col: 0.0})

    # Annual average (vectorized)
    poes = 1.0 / np.array(return_periods, dtype=float)
    ep_cols = [f"epop_{rp}" for rp in return_periods]
    vals = result[ep_cols].fillna(0.0).to_numpy()
    result["epop_ave"] = poes[-1] * vals[:, -1] - np.trapz(vals, poes, axis=1)

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_raster(flood_maps_dir: str, rp: int) -> str:
    """Locate the .tif file inside the RP_{rp} subfolder."""
    folder = os.path.join(flood_maps_dir, f"RP_{rp}")
    for fname in os.listdir(folder):
        if fname.endswith(".tif"):
            return os.path.join(folder, fname)
    raise FileNotFoundError(
        f"No .tif raster found for RP={rp} in: {folder}\n"
        f"Expected a subfolder named 'RP_{rp}' containing exactly one .tif file."
    )
