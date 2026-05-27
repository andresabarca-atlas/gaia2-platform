"""
GAIA 2.0 — Flood Impact Analysis: Chile
==========================================
Computes the Annual Average affected Population (AAP) due to floods
aggregated at the administrative level (ADM2).

No disaggregated point output or socio-economic enrichment (RWI / poverty)
is produced for this country — only boundary-level results.

Usage
-----
    python run_floods_chile.py
    python run_floods_chile.py --config config/settings.yaml

Outputs (written to paths.output_dir in settings.yaml)
-------
    adm2_flood_results.gpkg          ADM2 boundaries with exposure columns
"""

import argparse
from pathlib import Path

import geopandas as gpd
import yaml

from methodology.common.exposure import raster_to_points
from methodology.floods.impact import (
    aggregate_to_boundaries,
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
    print("[1/4] Loading boundaries...")
    boundaries = gpd.read_file(paths["boundaries"])

    # ------------------------------------------------------------------
    # 2. Build population point layer from raster
    # ------------------------------------------------------------------
    print("[2/4] Converting population raster to points...")
    pop_points = raster_to_points(paths["population_raster"])
    print(f"      {len(pop_points):,} population points loaded")

    # ------------------------------------------------------------------
    # 3. Sample flood depth at each point for every return period
    # ------------------------------------------------------------------
    print("[3/4] Sampling flood exposure per return period...")
    pop_points = sample_flood_exposure(
        pop_points,
        flood_maps_dir=paths["flood_maps_dir"],
        return_periods=return_periods,
        threshold=threshold,
    )

    # ------------------------------------------------------------------
    # 4. Aggregate to boundaries and compute Annual Average Population
    # ------------------------------------------------------------------
    print("[4/4] Aggregating to boundaries and computing AAP...")
    boundaries_out = aggregate_to_boundaries(pop_points, boundaries, return_periods)

    # ------------------------------------------------------------------
    # Save outputs
    # ------------------------------------------------------------------
    adm2_path = out_dir / "adm2_flood_results.gpkg"
    boundaries_out.to_file(adm2_path, driver="GPKG")

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
    print("─────────────────────────────────────────────")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GAIA 2.0 — Flood impact analysis: Chile"
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to YAML config file (default: config/settings.yaml)",
    )
    args = parser.parse_args()
    main(args.config)
