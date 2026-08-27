#!/usr/bin/env python3
"""Deterministic pre-solve gate for the Philippines v32 rice candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


YEARS = [str(year) for year in range(2020, 2054)]
MODES = {11: "rainfed", 19: "irrigated"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    baseline = args.baseline.resolve()
    candidate = args.candidate.resolve()
    checks: dict[str, object] = {}

    base_gen = json.loads((baseline / "genData.json").read_text())
    cand_gen = json.loads((candidate / "genData.json").read_text())
    identity_differences = {}
    for key in sorted(set(base_gen) | set(cand_gen)):
        if base_gen.get(key) != cand_gen.get(key):
            identity_differences[key] = [base_gen.get(key), cand_gen.get(key)]
    checks["genData_only_identity_changed"] = set(identity_differences) == {
        "osy-casename",
        "osy-desc",
        "osy-date",
    }

    tech_ids = {
        row["TechId"]: int(row["Tech"][-2:])
        for row in cand_gen["osy-tech"]
        if row["Tech"].startswith("LNDAGRPHLC")
    }
    rice_id = next(row["CommId"] for row in cand_gen["osy-comm"] if row["Comm"] == "CRPRCP")
    base_oar = json.loads((baseline / "RYTCM.json").read_text())
    cand_oar = json.loads((candidate / "RYTCM.json").read_text())
    base_rows = base_oar["OAR"]["SC_0"]
    cand_rows = cand_oar["OAR"]["SC_0"]
    checks["oar_row_count_unchanged"] = len(base_rows) == len(cand_rows)

    changed_cells = []
    forbidden_changes = []
    for index, (before, after) in enumerate(zip(base_rows, cand_rows)):
        for key in sorted(set(before) | set(after)):
            if before.get(key) == after.get(key):
                continue
            allowed = (
                key in YEARS
                and before.get("TechId") in tech_ids
                and before.get("CommId") == rice_id
                and before.get("MoId") in MODES
            )
            item = {"row": index, "field": key, "before": before.get(key), "after": after.get(key)}
            (changed_cells if allowed else forbidden_changes).append(item)
    checks["exactly_544_allowed_oar_cells_changed"] = len(changed_cells) == 544
    checks["no_forbidden_rytcM_changes"] = not forbidden_changes

    anchors = pd.read_csv(
        candidate
        / "data_sources/evidence/v32_rice_spatial_yield/derived/phl_rice_cluster_yields_2020.csv"
    )
    anchor_map = {
        (row.regime, int(row.clusters_yield)): float(row.model_oar_mt_per_1000km2)
        for row in anchors.itertuples()
    }
    anchor_checks = []
    index_checks = []
    for before, after in zip(base_rows, cand_rows):
        cluster = tech_ids.get(after.get("TechId"))
        regime = MODES.get(after.get("MoId"))
        if cluster is None or regime is None or after.get("CommId") != rice_id:
            continue
        anchor_checks.append(abs(float(after["2020"]) - anchor_map[(regime, cluster)]) < 1e-13)
        for year in YEARS:
            base_ratio = float(before[year]) / float(before["2020"])
            cand_ratio = float(after[year]) / float(after["2020"])
            index_checks.append(abs(base_ratio - cand_ratio) < 1e-13)
    checks["all_16_anchors_exact"] = len(anchor_checks) == 16 and all(anchor_checks)
    checks["all_544_fofa_indices_preserved"] = len(index_checks) == 544 and all(index_checks)

    reconstructed = anchors.groupby("regime").agg(
        production_mt=("reconstructed_production_mt", "sum"),
        physical_area=("benchmark_physical_area_1000km2", "sum"),
    )
    checks["benchmark_reconstruction"] = {
        "irrigated_production_mt": float(reconstructed.loc["irrigated", "production_mt"]),
        "irrigated_area_1000km2": float(reconstructed.loc["irrigated", "physical_area"]),
        "rainfed_production_mt": float(reconstructed.loc["rainfed", "production_mt"]),
        "rainfed_area_1000km2": float(reconstructed.loc["rainfed", "physical_area"]),
    }
    checks["benchmark_reconstruction_exact"] = (
        abs(checks["benchmark_reconstruction"]["irrigated_production_mt"] - 14.57176519) < 1e-10
        and abs(checks["benchmark_reconstruction"]["irrigated_area_1000km2"] - 20.06) < 1e-10
        and abs(checks["benchmark_reconstruction"]["rainfed_production_mt"] - 4.72309035) < 1e-10
        and abs(checks["benchmark_reconstruction"]["rainfed_area_1000km2"] - 14.6544173) < 1e-10
    )

    unchanged = {}
    for path in sorted(baseline.glob("RY*.json")):
        if path.name == "RYTCM.json":
            continue
        candidate_path = candidate / path.name
        unchanged[path.name] = sha256(path) == sha256(candidate_path)
    checks["all_other_parameter_json_unchanged"] = all(unchanged.values())
    checks["unchanged_parameter_files"] = unchanged
    checks["no_activity_or_share_constraint_change"] = all(
        unchanged.get(name, False) for name in ["RYT.json", "RYC.json", "RYTs.json"]
    )

    scalar_checks = [value for value in checks.values() if isinstance(value, bool)]
    status = "pass" if all(scalar_checks) else "fail"
    report = {
        "case": "Philippines_v32",
        "gate": "rice_spatial_yield_deterministic_pre_solve",
        "status": status,
        "optimizer_runs": 0,
        "equation_mapping": {
            "source": "RYTCM.json / OAR / SC_0",
            "generated": "OutputActivityRatio",
            "formulation": "AnnualTechnologyProductionByMode and commodity balance in SOLVERs/model.v.5.4.txt",
            "effect": "Rice output per unit of endogenous land-technology activity",
        },
        "classification": {
            "rice_demand": "exogenous final demand",
            "irrigation_service_20_06": "inherited physical stock",
            "rice_regime_area_and_production": "benchmark-only validation values",
            "land_cluster_technologies": "physical land/water-to-crop conversions",
        },
        "checks": checks,
        "identity_differences": identity_differences,
        "forbidden_changes": forbidden_changes,
    }
    output = candidate / "documentation/preflight_rice_spatial_yield_v32.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
