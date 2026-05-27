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

    # Extract coordinates and population as numpy arrays once — avoids 3.5M Python geometry iterations
    xs = points.geometry.x.to_numpy()
    ys = points.geometry.y.to_numpy()
    pop = points["population"].to_numpy()

    rows = cols = None

    for rp in return_periods:
        raster_path = _find_raster(flood_maps_dir, rp)
        with rasterio.open(raster_path) as src:
            if rows is None:
                # All RP rasters share the same grid — compute pixel indices once and reuse
                rows, cols = rasterio.transform.rowcol(src.transform, xs, ys)
                rows = np.clip(np.asarray(rows, dtype=np.intp), 0, src.height - 1)
                cols = np.clip(np.asarray(cols, dtype=np.intp), 0, src.width - 1)
            data = src.read(1)  # read full band into memory
            nodata = src.nodata

        depths = data[rows, cols].astype(float)
        if nodata is not None:
            depths[depths == nodata] = 0.0

        points[f"exposed_{rp}"] = np.where(depths > threshold, pop, 0.0)

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
    aap = poes[-1] * vals[:, -1] - np.trapezoid(vals, poes, axis=1)

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

    # Exposed population per return period — single groupby over all columns at once
    exp_cols = [f"exposed_{rp}" for rp in return_periods]
    rename_map = {f"exposed_{rp}": f"epop_{rp}" for rp in return_periods}
    exp_sums = joined.groupby(joined.index_right)[exp_cols].sum().rename(columns=rename_map)
    result = result.join(exp_sums).fillna({c: 0.0 for c in rename_map.values()})

    # Annual average (vectorized)
    poes = 1.0 / np.array(return_periods, dtype=float)
    ep_cols = [f"epop_{rp}" for rp in return_periods]
    vals = result[ep_cols].fillna(0.0).to_numpy()
    result["epop_ave"] = poes[-1] * vals[:, -1] - np.trapezoid(vals, poes, axis=1)

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def detect_return_periods(flood_maps_dir: str) -> list:
    """
    Scan flood_maps_dir for subfolders named RP_{n} or RP{n} and return the
    sorted list of integer return periods found.

    Raises ValueError if no valid RP folders are found.
    """
    import re
    pattern = re.compile(r"^RP_?(\d+)$")
    rps = []
    for name in os.listdir(flood_maps_dir):
        m = pattern.match(name)
        if m and os.path.isdir(os.path.join(flood_maps_dir, name)):
            rps.append(int(m.group(1)))
    if not rps:
        raise ValueError(
            f"No RP folders found in: {flood_maps_dir}\n"
            f"Expected folders named RP10, RP20, ... or RP_10, RP_20, ..."
        )
    return sorted(rps)


def _find_raster(flood_maps_dir: str, rp: int) -> str:
    """Locate the .tif file inside the RP_{rp} or RP{rp} subfolder."""
    for folder_name in (f"RP_{rp}", f"RP{rp}"):
        folder = os.path.join(flood_maps_dir, folder_name)
        if os.path.isdir(folder):
            for fname in os.listdir(folder):
                if fname.endswith(".tif"):
                    return os.path.join(folder, fname)
    raise FileNotFoundError(
        f"No .tif raster found for RP={rp} in: {flood_maps_dir}\n"
        f"Expected a subfolder named 'RP_{rp}' or 'RP{rp}' containing a .tif file."
    )
