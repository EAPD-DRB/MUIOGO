#!/usr/bin/env python3
"""Post-solve rice outcome gate for the Philippines v32 BASE candidate."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


RICE_MODES = {11: "rainfed", 19: "irrigated"}
ACTIVE_IRRIGATED_MODES = {5, 6, 10, 16, 19, 22}
BENCHMARK = {
    "irrigated_area_1000km2": 20.06,
    "rainfed_area_1000km2": 14.6544173,
    "irrigated_production_mt": 14.57176519,
    "rainfed_production_mt": 4.72309035,
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    return parser.parse_args()


def activities(results: Path) -> tuple[str, dict[tuple[str, int], float]]:
    pattern = re.compile(
        r"^\s*\d+\s+TotalAnnualTechnologyActivityByMode\(RE1,([^,]+),(\d+),2020\)"
        r"\s+([-+0-9.eE]+)"
    )
    values: dict[tuple[str, int], float] = {}
    with results.open() as stream:
        status = stream.readline().strip()
        for line in stream:
            match = pattern.match(line)
            if match:
                values[(match.group(1), int(match.group(2)))] = float(match.group(3))
    return status, values


def rice_oar(case: Path) -> dict[tuple[str, int], float]:
    gen = json.loads((case / "genData.json").read_text())
    tech = {
        row["TechId"]: row["Tech"]
        for row in gen["osy-tech"]
        if row["Tech"].startswith("LNDAGRPHLC")
    }
    rice_id = next(row["CommId"] for row in gen["osy-comm"] if row["Comm"] == "CRPRCP")
    rows = json.loads((case / "RYTCM.json").read_text())["OAR"]["SC_0"]
    return {
        (tech[row["TechId"]], int(row["MoId"])): float(row["2020"])
        for row in rows
        if row.get("TechId") in tech
        and row.get("CommId") == rice_id
        and int(row.get("MoId", -1)) in RICE_MODES
    }


def summarize(case: Path, run: str) -> dict[str, object]:
    status, activity = activities(case / "res" / run / "results.txt")
    oar = rice_oar(case)
    cluster_rows = []
    by_regime = {
        regime: {"area_1000km2": 0.0, "production_mt": 0.0}
        for regime in RICE_MODES.values()
    }
    for cluster in range(1, 9):
        technology = f"LNDAGRPHLC{cluster:02d}"
        for mode, regime in RICE_MODES.items():
            area = activity.get((technology, mode), 0.0)
            production = area * oar[(technology, mode)]
            by_regime[regime]["area_1000km2"] += area
            by_regime[regime]["production_mt"] += production
            cluster_rows.append(
                {
                    "cluster": cluster,
                    "regime": regime,
                    "mode": mode,
                    "area_1000km2": area,
                    "oar_mt_per_1000km2": oar[(technology, mode)],
                    "production_mt": production,
                }
            )
    competing_irrigated = sum(
        value
        for (technology, mode), value in activity.items()
        if technology.startswith("LNDAGRPHLC")
        and mode in ACTIVE_IRRIGATED_MODES - {19}
    )
    irrigation = activity.get(("PHL_AGR_IRRIGATION", 1), 0.0)
    surface = activity.get(("DEMAGRSURPHL", 1), 0.0)
    groundwater = activity.get(("DEMAGRGWTPHL", 1), 0.0)
    return {
        "status": status,
        "rice_by_regime": by_regime,
        "rice_by_cluster": cluster_rows,
        "total_rice_area_1000km2": sum(item["area_1000km2"] for item in by_regime.values()),
        "total_rice_production_mt": sum(item["production_mt"] for item in by_regime.values()),
        "irrigation_service_use_1000km2": irrigation,
        "nonrice_irrigated_crop_area_1000km2": competing_irrigated,
        "surface_withdrawal_km3": surface,
        "groundwater_withdrawal_km3": groundwater,
    }


def pct(value: float, benchmark: float) -> float:
    return (value / benchmark - 1.0) * 100.0


def main() -> None:
    args = arguments()
    baseline = summarize(args.baseline.resolve(), "BASE_V31")
    candidate = summarize(args.candidate.resolve(), "BASE_V32_RICE_YIELD")
    candidate_regime = candidate["rice_by_regime"]
    total_benchmark_area = BENCHMARK["irrigated_area_1000km2"] + BENCHMARK["rainfed_area_1000km2"]
    total_benchmark_production = BENCHMARK["irrigated_production_mt"] + BENCHMARK["rainfed_production_mt"]
    comparison = {
        "irrigated_area_error_percent": pct(candidate_regime["irrigated"]["area_1000km2"], BENCHMARK["irrigated_area_1000km2"]),
        "rainfed_area_error_percent": pct(candidate_regime["rainfed"]["area_1000km2"], BENCHMARK["rainfed_area_1000km2"]),
        "total_area_error_percent": pct(candidate["total_rice_area_1000km2"], total_benchmark_area),
        "irrigated_production_error_percent": pct(candidate_regime["irrigated"]["production_mt"], BENCHMARK["irrigated_production_mt"]),
        "rainfed_production_error_percent": pct(candidate_regime["rainfed"]["production_mt"], BENCHMARK["rainfed_production_mt"]),
        "total_production_error_percent": pct(candidate["total_rice_production_mt"], total_benchmark_production),
    }
    gates = {
        "candidate_optimal": str(candidate["status"]).startswith("Optimal"),
        "irrigated_area_within_10_percent": abs(comparison["irrigated_area_error_percent"]) <= 10.0,
        "irrigated_production_within_10_percent": abs(comparison["irrigated_production_error_percent"]) <= 10.0,
        "rainfed_production_within_20_percent": abs(comparison["rainfed_production_error_percent"]) <= 20.0,
        "total_rice_area_within_15_percent": abs(comparison["total_area_error_percent"]) <= 15.0,
        "total_rice_production_balance_within_0_01_percent": abs(comparison["total_production_error_percent"]) <= 0.01,
        "irrigation_service_use_within_10_percent": abs(pct(candidate["irrigation_service_use_1000km2"], 20.06)) <= 10.0,
        "surface_withdrawal_in_predicted_39_to_71_km3_range": 39.0 <= candidate["surface_withdrawal_km3"] <= 71.0,
    }
    advisories = {
        "rainfed_area_within_10_percent": abs(comparison["rainfed_area_error_percent"]) <= 10.0,
        "groundwater_withdrawal_nonzero": candidate["groundwater_withdrawal_km3"] > 1e-8,
        "rice_uses_all_shared_irrigation": candidate_regime["irrigated"]["area_1000km2"] >= candidate["irrigation_service_use_1000km2"] - 1e-4,
        "cluster_concentration": [
            row for row in candidate["rice_by_cluster"] if row["area_1000km2"] > 1e-6
        ],
    }
    report = {
        "case": "Philippines_v32",
        "gate": "BASE rice reconstruction plus endogenous-allocation validation",
        "status": "pass_with_advisories" if all(gates.values()) else "fail",
        "optimizer_runs_in_candidate": 1,
        "benchmarks_not_constraints": BENCHMARK,
        "baseline_v31": baseline,
        "candidate_v32": candidate,
        "benchmark_comparison": comparison,
        "gates": gates,
        "advisories": advisories,
    }
    output = args.candidate.resolve() / "documentation/rice_spatial_yield_base_validation_v32.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if report["status"] == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
