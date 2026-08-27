#!/usr/bin/env python3
"""Derive non-forcing 2020 rice OAR anchors by CLEWs agro-ecological cluster.

This script is the reproducible method behind the Philippines v32 rice-yield
candidate. It joins the exact regenerated CLEWs Global cell clusters to GADM
4.1 level-1 areas, then allocates official PSA OpenSTAT production and
harvested area across clusters by each province's intersected land shares.

It requires pandas, geopandas, pyogrio/fiona, and a projected-area backend.
The repository's normal MUIOGO virtual environment intentionally does not
carry these geospatial dependencies; the retained derived CSVs are therefore
the authoritative no-rerun inputs for rebuilding the model coefficients.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd


NAME_MAP = {
    "Cotabato (North Cotabato)": "North Cotabato",
    "Davao de Oro (Compostela Valley)": "Compostela Valley",
    "Tawi-tawi": "Tawi-Tawi",
    "Maguindanao del Norte": "Maguindanao",
    "Maguindanao del Sur": "Maguindanao",
    "Davao Occidental": "Davao del Sur",
    "City of Davao": "Davao del Sur",
    "Zamboanga City": "Zamboanga del Sur",
    "Puerto Princesa City": "Palawan",
    "Bacolod City": "Negros Occidental",
    "Butuan City": "Agusan del Norte",
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cluster-gpkg", type=Path, required=True)
    parser.add_argument("--gadm1-shp", type=Path, required=True)
    parser.add_argument("--production-csv", type=Path, required=True)
    parser.add_argument("--area-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--irrigated-physical-area-ha", type=float, default=2_006_000.0)
    return parser.parse_args()


def read_psa(path: Path, value_name: str) -> pd.DataFrame:
    raw = pd.read_csv(path)
    value_col = raw.columns[-1]
    raw[value_col] = pd.to_numeric(raw[value_col], errors="coerce")
    raw = raw.loc[raw["Geolocation"].str.startswith("....", na=False)].copy()
    raw["province"] = raw["Geolocation"].str.removeprefix("....")
    raw = raw.loc[~raw["province"].str.endswith((" a/", " b/", " c/"))].copy()
    raw["province"] = raw["province"].replace(NAME_MAP)
    raw["regime"] = (
        raw["Ecosystem/Croptype"]
        .str.replace(" Palay", "", regex=False)
        .str.lower()
    )
    return (
        raw.groupby(["province", "regime"], as_index=False)[value_col]
        .sum(min_count=1)
        .rename(columns={value_col: value_name})
    )


def main() -> None:
    args = arguments()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    cells = gpd.read_file(args.cluster_gpkg)[
        ["id", "clusters_yield", "sqkm", "geometry"]
    ]
    adm1 = gpd.read_file(args.gadm1_shp)[["NAME_1", "geometry"]].rename(
        columns={"NAME_1": "province"}
    )

    cells_ea = cells.to_crs(6933)
    adm1_ea = adm1.to_crs(6933)
    overlay = gpd.overlay(cells_ea, adm1_ea, how="intersection", keep_geom_type=False)
    overlay["intersection_m2"] = overlay.geometry.area
    cell_area = cells_ea.set_index("id").geometry.area.rename("cell_m2")
    overlay = overlay.join(cell_area, on="id")
    overlay["allocated_sqkm"] = (
        overlay["sqkm"] * overlay["intersection_m2"] / overlay["cell_m2"]
    )
    shares = overlay.groupby(
        ["province", "clusters_yield"], as_index=False
    )["allocated_sqkm"].sum()
    shares["province_land_sqkm"] = shares.groupby("province")[
        "allocated_sqkm"
    ].transform("sum")
    shares["province_cluster_share"] = (
        shares["allocated_sqkm"] / shares["province_land_sqkm"]
    )

    production = read_psa(args.production_csv, "production_t")
    area = read_psa(args.area_csv, "harvested_area_ha")
    psa = production.merge(area, on=["province", "regime"], how="outer")
    psa[["production_t", "harvested_area_ha"]] = psa[
        ["production_t", "harvested_area_ha"]
    ].fillna(0.0)

    nonzero = psa.loc[
        (psa.production_t != 0) | (psa.harvested_area_ha != 0), "province"
    ]
    unknown = sorted(set(nonzero) - set(adm1.province))
    if unknown:
        raise SystemExit(f"Unmapped nonzero PSA geographies: {unknown}")

    allocation = shares.merge(psa, on="province", how="left")
    allocation[["production_t", "harvested_area_ha"]] = allocation[
        ["production_t", "harvested_area_ha"]
    ].fillna(0.0)
    allocation["allocated_production_t"] = (
        allocation["production_t"] * allocation["province_cluster_share"]
    )
    allocation["allocated_harvested_area_ha"] = (
        allocation["harvested_area_ha"] * allocation["province_cluster_share"]
    )

    summary = allocation.groupby(
        ["regime", "clusters_yield"], as_index=False
    )[["allocated_production_t", "allocated_harvested_area_ha"]].sum()
    summary["achieved_yield_t_per_harvested_ha"] = (
        summary["allocated_production_t"]
        / summary["allocated_harvested_area_ha"]
    )
    irrigated_harvested_area_ha = psa.loc[
        psa.regime.eq("irrigated"), "harvested_area_ha"
    ].sum()
    cropping_intensity = (
        irrigated_harvested_area_ha / args.irrigated_physical_area_ha
    )
    summary["cropping_intensity"] = 1.0
    summary.loc[
        summary.regime.eq("irrigated"), "cropping_intensity"
    ] = cropping_intensity
    summary["model_oar_mt_per_1000km2"] = (
        summary["achieved_yield_t_per_harvested_ha"]
        * summary["cropping_intensity"]
        / 10.0
    )
    summary["benchmark_physical_area_1000km2"] = (
        summary["allocated_harvested_area_ha"] / 100_000.0
    )
    summary.loc[
        summary.regime.eq("irrigated"), "benchmark_physical_area_1000km2"
    ] /= cropping_intensity
    summary["reconstructed_production_mt"] = (
        summary["model_oar_mt_per_1000km2"]
        * summary["benchmark_physical_area_1000km2"]
    )

    allocation.to_csv(
        args.output_dir / "phl_rice_province_cluster_allocation_2020.csv",
        index=False,
    )
    summary.to_csv(
        args.output_dir / "phl_rice_cluster_yields_2020.csv", index=False
    )

    checks = summary.groupby("regime").agg(
        production_mt=("reconstructed_production_mt", "sum"),
        physical_area_1000km2=("benchmark_physical_area_1000km2", "sum"),
    )
    checks["weighted_oar_mt_per_1000km2"] = (
        checks.production_mt / checks.physical_area_1000km2
    )
    print(checks.to_string())


if __name__ == "__main__":
    main()
