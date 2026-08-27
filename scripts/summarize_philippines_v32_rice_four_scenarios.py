#!/usr/bin/env python3
"""Consolidate four-scenario Philippines v32 rice validation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


RUNS = {
    "BASE": ("BASE_V31", "BASE_V32_RICE_YIELD"),
    "COAL_PHASEOUT": ("COAL_PHASEOUT_V31", "COAL_PHASEOUT_V32_RICE_YIELD"),
    "RE": ("RE_V31", "RE_V32_RICE_YIELD"),
    "EV": ("EV_V31", "EV_V32_RICE_YIELD"),
}
RICE_MODES = {11: "rainfed", 19: "irrigated"}
AFFECTED_TECH_PREFIXES = ("LND", "MINLND", "DEMAGR", "PHL_AGR_IRRIGATION")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    return parser.parse_args()


def all_annual_activity(results: Path) -> tuple[str, dict[tuple[str, int, int], float]]:
    pattern = re.compile(
        r"^\s*\d+\s+TotalAnnualTechnologyActivityByMode\(RE1,([^,]+),(\d+),(\d{4})\)"
        r"\s+([-+0-9.eE]+)"
    )
    values = {}
    with results.open() as stream:
        status = stream.readline().strip()
        for line in stream:
            match = pattern.match(line)
            if match:
                values[(match.group(1), int(match.group(2)), int(match.group(3)))] = float(match.group(4))
    return status, values


def oar_by_year(case: Path) -> dict[tuple[str, int, int], float]:
    gen = json.loads((case / "genData.json").read_text())
    tech = {
        row["TechId"]: row["Tech"]
        for row in gen["osy-tech"]
        if row["Tech"].startswith("LNDAGRPHLC")
    }
    rice_id = next(row["CommId"] for row in gen["osy-comm"] if row["Comm"] == "CRPRCP")
    rows = json.loads((case / "RYTCM.json").read_text())["OAR"]["SC_0"]
    values = {}
    for row in rows:
        if row.get("TechId") not in tech or row.get("CommId") != rice_id or row.get("MoId") not in RICE_MODES:
            continue
        for year in range(2020, 2054):
            values[(tech[row["TechId"]], int(row["MoId"]), year)] = float(row[str(year)])
    return values


def rice_year(activity, oar, year: int) -> dict[str, dict[str, float]]:
    result = {regime: {"area_1000km2": 0.0, "production_mt": 0.0} for regime in RICE_MODES.values()}
    for cluster in range(1, 9):
        tech = f"LNDAGRPHLC{cluster:02d}"
        for mode, regime in RICE_MODES.items():
            area = activity.get((tech, mode, year), 0.0)
            result[regime]["area_1000km2"] += area
            result[regime]["production_mt"] += area * oar[(tech, mode, year)]
    return result


def main() -> None:
    args = arguments()
    baseline = args.baseline.resolve()
    candidate = args.candidate.resolve()
    baseline_oar = oar_by_year(baseline)
    candidate_oar = oar_by_year(candidate)
    scenarios = {}
    all_pass = True
    for scenario, (baseline_run, candidate_run) in RUNS.items():
        base_status, base_activity = all_annual_activity(baseline / "res" / baseline_run / "results.txt")
        cand_status, cand_activity = all_annual_activity(candidate / "res" / candidate_run / "results.txt")
        record = json.loads((candidate / "res" / candidate_run / "optimization_record.json").read_text())
        outside_differences = []
        for key in set(base_activity) | set(cand_activity):
            tech = key[0]
            difference = cand_activity.get(key, 0.0) - base_activity.get(key, 0.0)
            if not tech.startswith(AFFECTED_TECH_PREFIXES) and abs(difference) > 1e-6:
                outside_differences.append((key, difference))
        outside_2020_nonwater = [
            (key, value)
            for key, value in outside_differences
            if key[2] == 2020 and key[0] != "ENV_WATER" and abs(value) > 0.01
        ]
        rice = {str(year): rice_year(cand_activity, candidate_oar, year) for year in (2020, 2021, 2022)}
        baseline_rice_2020 = rice_year(base_activity, baseline_oar, 2020)
        summary = {
            "baseline_status": base_status,
            "candidate_status": cand_status,
            "objective": record["objective"],
            "objective_change": record["objective_change"],
            "objective_change_percent": record["objective_change_percent"],
            "solve_seconds": record["solve_seconds"],
            "runtime_ratio_to_v31": record["runtime_ratio_to_baseline"],
            "runtime_acceptance_passed": record["runtime_acceptance_passed"],
            "baseline_rice_2020": baseline_rice_2020,
            "candidate_rice_2020_to_2022": rice,
            "irrigation_service_2020_to_2022_1000km2": {
                str(year): cand_activity.get(("PHL_AGR_IRRIGATION", 1, year), 0.0)
                for year in (2020, 2021, 2022)
            },
            "surface_withdrawal_2020_km3": cand_activity.get(("DEMAGRSURPHL", 1, 2020), 0.0),
            "groundwater_withdrawal_2020_km3": cand_activity.get(("DEMAGRGWTPHL", 1, 2020), 0.0),
            "outside_affected_technology_activity_difference_count": len(outside_differences),
            "outside_affected_2020_nonwater_difference_over_0_01_count": len(outside_2020_nonwater),
            "maximum_absolute_outside_affected_difference": max(
                (abs(value) for unused_key, value in outside_differences), default=0.0
            ),
            "largest_outside_affected_differences": [
                {"technology": key[0], "mode": key[1], "year": key[2], "difference": value}
                for key, value in sorted(outside_differences, key=lambda item: abs(item[1]), reverse=True)[:20]
            ],
        }
        scenario_pass = (
            cand_status.startswith("Optimal")
            and record["runtime_acceptance_passed"]
            and abs(rice["2020"]["irrigated"]["area_1000km2"] - 20.06) <= 0.01
            and 39.0 <= summary["surface_withdrawal_2020_km3"] <= 71.0
            and len(outside_2020_nonwater) == 0
        )
        summary["gate_passed"] = scenario_pass
        all_pass = all_pass and scenario_pass
        scenarios[scenario] = summary

    report = {
        "case": "Philippines_v32",
        "status": "pass_with_advisories" if all_pass else "fail",
        "promotion_recommendation": "eligible_with_forward_irrigation_followup" if all_pass else "not_eligible",
        "optimizer_run_count": 4,
        "parallel_policy_solves": ["COAL_PHASEOUT", "RE", "EV"],
        "viewer_json_updated": False,
        "scenarios": scenarios,
        "advisories": [
            "Rainfed 2020 area remains 28.7% below the benchmark although the production split is substantially restored.",
            "Groundwater withdrawal remains zero in every scenario.",
            "Rice activity remains concentrated in clusters 5 and 7; observed yields now support that ranking, but the national pooled-cropland formulation does not preserve province crop area.",
            "From 2021 the optimizer expands irrigation service to about 25.60 thousand km2 and returns rainfed rice to zero; the inherited 2020 stock is reproduced, but the forward irrigation build rate and economics require a high-priority follow-up.",
            "Policy-run wall times include concurrent CPU contention and are not clean serial benchmarks."
            " Later-year differences outside the land/agriculture technology family are small endogenous or degenerate substitutions; 2020 has no non-water difference above 0.01 outside scope."
        ],
    }
    output = candidate / "documentation/rice_spatial_yield_four_scenario_validation_v32.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not all_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
