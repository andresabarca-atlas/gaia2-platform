"""
GAIA 2.0 — Flood Impact Analysis: Ecuador
==========================================
Computes the Annual Average affected Population (AAP) due to floods at two levels:
  1. Administrative boundaries (ADM2) — for the dashboard
  2. Individual population points — for granular analysis

Usage
-----
    python run_floods_ecuador.py
    python run_floods_ecuador.py --config config/settings.yaml

Outputs (written to paths.output_dir in settings.yaml)
-------
    adm2_flood_results.gpkg          ADM2 boundaries with exposure columns
    population_points_flood.csv      Point-level results (exposed points only)
"""

import argparse
from pathlib import Path

import pandas as pd
import geopandas as gpd
import yaml

from methodology.common.exposure import assign_rwi, raster_to_points
from methodology.floods.impact import (
    aggregate_to_boundaries,
    calculate_annual_average,
    detect_return_periods,
    sample_flood_exposure,
)


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main(config_path: str = "config/settings.yaml") -> None:
    cfg = load_config(config_path)
    paths = cfg["paths"]
    params = cfg["parameters"]

    threshold = params["flood_threshold"]
    return_periods = detect_return_periods(paths["flood_maps_dir"])
    print(f"      Return periods detected: {return_periods}")
    out_dir = Path(paths["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Load administrative boundaries
    # ------------------------------------------------------------------
    print("[1/5] Loading boundaries...")
    boundaries = gpd.read_file(paths["boundaries"])

    # ------------------------------------------------------------------
    # 2. Build population point layer from raster
    # ------------------------------------------------------------------
    print("[2/5] Converting population raster to points...")
    pop_points = raster_to_points(paths["population_raster"])
    pop_points["longitude"] = pop_points.geometry.x
    pop_points["latitude"] = pop_points.geometry.y
    print(f"      {len(pop_points):,} population points loaded")

    # ------------------------------------------------------------------
    # 3. Assign Relative Wealth Index to each point
    # ------------------------------------------------------------------
    print("[3/5] Assigning Relative Wealth Index (nearest-neighbor)...")
    pop_points = assign_rwi(pop_points, paths["rwi"])

    # ------------------------------------------------------------------
    # 4. Sample flood depth at each point for every return period
    # ------------------------------------------------------------------
    print("[4/5] Sampling flood exposure per return period...")
    pop_points = sample_flood_exposure(
        pop_points,
        flood_maps_dir=paths["flood_maps_dir"],
        return_periods=return_periods,
        threshold=threshold,
    )

    # ------------------------------------------------------------------
    # 5. Compute Annual Average affected Population
    # ------------------------------------------------------------------
    print("[5/5] Computing Annual Average Population (AAP)...")

    # Point-level AAP
    pop_points = calculate_annual_average(pop_points, return_periods=return_periods)
    pop_points_out = pop_points[pop_points["epop_ave"] > 0].copy()

    # Boundary-level aggregation + AAP
    boundaries_out = aggregate_to_boundaries(pop_points, boundaries, return_periods)

    # ------------------------------------------------------------------
    # Optional enrichment: poverty rate by ADM2
    # ------------------------------------------------------------------
    poverty_path = Path(paths.get("poverty_data", "data/raw/poverty_data.csv"))
    if poverty_path.exists():
        print("[+] Poverty data found — joining POVERTY_RA to ADM2 results...")
        poverty_df = pd.read_csv(poverty_path, usecols=["CC_2", "POVERTY_RA"])
        # Normalize CC_2: GeoPackage stores it as zero-padded string ("0115"),
        # CSV stores it as integer (115). Convert both to int for the join.
        boundaries_out["_cc2_int"] = (
            pd.to_numeric(boundaries_out["CC_2"], errors="coerce").astype("Int64")
        )
        poverty_df["CC_2"] = pd.to_numeric(poverty_df["CC_2"], errors="coerce").astype("Int64")
        boundaries_out = boundaries_out.merge(
            poverty_df, left_on="_cc2_int", right_on="CC_2", how="left", suffixes=("", "_pov")
        ).drop(columns=["_cc2_int", "CC_2_pov"])
        matched = boundaries_out["POVERTY_RA"].notna().sum()
        print(f"      {matched}/{len(boundaries_out)} cantons matched with poverty data")
        # Derived: average affected population living in poverty
        # POVERTY_RA is a percentage (0–100), so divide by 100 before multiplying
        boundaries_out["epop_poverty"] = (boundaries_out["POVERTY_RA"] / 100) * boundaries_out["epop_ave"]
    else:
        print("[~] No poverty data found — skipping (place poverty_data.csv in data/raw/ to enable)")

    # ------------------------------------------------------------------
    # Save outputs
    # ------------------------------------------------------------------
    adm2_path = out_dir / "adm2_flood_results.gpkg"
    points_path = out_dir / "population_points_flood.csv"

    boundaries_out.to_file(adm2_path, driver="GPKG")
    exposed_cols = [c for c in pop_points_out.columns if c.startswith("exposed_")]
    pop_points_out.drop(columns=["geometry"] + exposed_cols).to_csv(points_path, index=False)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    total_pop = boundaries_out["pop_tot"].sum()
    total_aap = boundaries_out["epop_ave"].sum()

    print("\n── Results ──────────────────────────────────")
    print(f"  Total population          : {total_pop:>12,.0f}")
    print(f"  Annual avg. affected (AAP): {total_aap:>12,.0f} people/year")
    print(f"  AAP / Total population    : {total_aap / total_pop:.2%}")
    print(f"\n  ADM2 results  → {adm2_path}")
    print(f"  Point results → {points_path}")
    print("─────────────────────────────────────────────")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GAIA 2.0 — Flood impact analysis"
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to YAML config file (default: config/settings.yaml)",
    )
    args = parser.parse_args()
    main(args.config)
