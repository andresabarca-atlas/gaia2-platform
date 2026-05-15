"""
GAIA 2.0 — Common exposure utilities
=====================================
Functions shared across all hazard types:
  - Convert a population raster to a point GeoDataFrame
  - Assign Relative Wealth Index (RWI) via nearest-neighbor join
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.transform import xy as raster_xy


def raster_to_points(raster_path: str) -> gpd.GeoDataFrame:
    """
    Convert a population raster to a GeoDataFrame of points.

    Each point represents the centroid of one raster pixel.
    Only pixels with a valid, positive population value are included.

    Parameters
    ----------
    raster_path : str
        Path to a GeoTIFF population raster (e.g. WorldPop 100m).

    Returns
    -------
    GeoDataFrame with columns: population, geometry (Point, original CRS).
    """
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        transform = src.transform
        nodata = src.nodata
        crs = src.crs

    rows, cols = np.where((data != nodata) & (data > 0))
    xs, ys = raster_xy(transform, rows, cols)

    return gpd.GeoDataFrame(
        {"population": data[rows, cols].astype(float)},
        geometry=gpd.points_from_xy(xs, ys),
        crs=crs,
    )


def assign_rwi(
    population_points: gpd.GeoDataFrame,
    rwi_path: str,
) -> gpd.GeoDataFrame:
    """
    Assign the Relative Wealth Index (RWI) to each population point via
    nearest-neighbor spatial join.

    The RWI dataset (Meta / Artifact, 2.4km tiles) has coarser resolution
    than the population raster, so each population point gets the RWI of its
    nearest RWI tile centroid.

    Parameters
    ----------
    population_points : GeoDataFrame
        Output of raster_to_points().
    rwi_path : str
        Path to the RWI CSV file. Must have columns: latitude, longitude, rwi.

    Returns
    -------
    GeoDataFrame — population_points with an added 'rwi' column.
    """
    rwi_df = pd.read_csv(rwi_path)
    rwi_gdf = gpd.GeoDataFrame(
        rwi_df[["rwi"]],
        geometry=gpd.points_from_xy(rwi_df.longitude, rwi_df.latitude),
        crs=population_points.crs,
    )

    # Reproject to a metric CRS for accurate distance-based nearest join
    pop_proj = population_points.to_crs(epsg=3857)
    rwi_proj = rwi_gdf.to_crs(epsg=3857)

    joined = gpd.sjoin_nearest(
        pop_proj,
        rwi_proj[["rwi", "geometry"]],
        how="left",
        distance_col="_dist",
    )
    joined = joined.drop(columns=["index_right", "_dist"])

    return joined.to_crs(population_points.crs)
