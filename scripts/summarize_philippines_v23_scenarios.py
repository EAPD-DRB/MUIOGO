#!/usr/bin/env python3
"""Consolidate Package 1 validation across BASE and all policy overlays."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "WebAPP" / "DataStorage" / ".Philippines_v23-package1-candidate-20260824"
RUNS = {
    "BASE": "PACKAGE1_V23_BASE",
    "COAL_PHASEOUT": "PACKAGE1_V23_COAL_PHASEOUT",
    "RE": "PACKAGE1_V23_RE",
    "EV": "PACKAGE1_V23_EV",
}
CLOSED = ("PHL_PRO_PROC_BIOF", "PHL_POW_GH2_COAL", "PHL_AGR_HEAT_COAL")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def annual_activity(run: Path) -> dict[str, float]:
    totals = {name: 0.0 for name in CLOSED}
    with (run / "csv" / "TotalAnnualTechnologyActivityByMode.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["t"] in totals:
                totals[row["t"]] += abs(float(row["TotalAnnualTechnologyActivityByMode"]))
    return totals


def reserve(run: Path) -> dict:
    pattern = re.compile(
        r"UDC1_UserDefinedConstraintInequality\(RE1,PHL_POW_RESERVE_MARGIN,(\d{4})\)\s+"
        r"([-+0-9.eE]+)\s+([-+0-9.eE]+)$"
    )
    rows = []
    for line in (run / "results.txt").read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            lhs = float(match.group(2))
            rows.append({"year": match.group(1), "lhs_gw": lhs, "headroom_gw": -lhs,
                         "dual": float(match.group(3))})
    return {
        "row_count": len(rows),
        "all_satisfied": len(rows) == 34 and all(row["lhs_gw"] <= 1e-7 for row in rows),
        "minimum_headroom_gw": min(row["headroom_gw"] for row in rows),
        "binding_years": [row["year"] for row in rows if row["headroom_gw"] <= 1e-7],
        "rows": rows,
    }


def main() -> None:
    scenarios = {}
    for scenario, run_name in RUNS.items():
        run = CASE / "res" / run_name
        optimization = json.loads((run / "optimization_record.json").read_text(encoding="utf-8"))
        matrix = json.loads((run / "generation_matrix_report.json").read_text(encoding="utf-8"))
        route_activity = annual_activity(run)
        reserve_result = reserve(run)
        scenarios[scenario] = {
            "run": str(run),
            "status": optimization["status"],
            "objective": optimization["objective"],
            "objective_change": optimization["objective_change"],
            "objective_change_percent": optimization["objective_change_percent"],
            "solve_seconds": optimization["solve_seconds"],
            "matrix_dimensions": matrix["matrix_dimensions"],
            "source_gate_hashes": matrix["source_gate_hashes"],
            "closed_route_absolute_activity_sums": route_activity,
            "reserve": reserve_result,
            "hashes": {
                "data.txt": sha256(run / "data.txt"), "lp.lp": sha256(run / "lp.lp"),
                "results.txt": sha256(run / "results.txt"),
            },
            "passed": (
                str(optimization["status"]).startswith("Optimal")
                and matrix["status"] == "passed"
                and reserve_result["all_satisfied"]
                and all(value <= 1e-7 for value in route_activity.values())
            ),
        }
    report = {
        "schema": "philippines-v23-package1-four-scenario-validation-v1",
        "candidate": str(CASE),
        "status": "passed" if all(item["passed"] for item in scenarios.values()) else "failed",
        "scenarios": scenarios,
        "optimizer_runs": 4,
        "optimizer_run_purposes": {
            "BASE": "Required coupled candidate feasibility and optimality proof.",
            "COAL_PHASEOUT": "User-required policy-overlay feasibility and optimality proof.",
            "RE": "User-required policy-overlay feasibility and optimality proof after its source gate caught and prevented an impossible candidate.",
            "EV": "User-required policy-overlay feasibility and optimality proof.",
        },
        "execution": "BASE first; the other three CBC runs concurrently in isolated run directories; no shared viewer generation.",
        "promotion_allowed": all(item["passed"] for item in scenarios.values()),
    }
    output = CASE / "documentation" / "package1_v23_four_scenario_validation.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output), "status": report["status"], "optimizer_runs": 4,
        "scenarios": {name: {
            "status": item["status"], "objective": item["objective"],
            "objective_change_percent": item["objective_change_percent"],
            "solve_seconds": item["solve_seconds"], "reserve_satisfied": item["reserve"]["all_satisfied"],
            "closed_routes_zero": all(value <= 1e-7 for value in item["closed_route_absolute_activity_sums"].values()),
        } for name, item in scenarios.items()},
        "promotion_allowed": report["promotion_allowed"],
    }, indent=2))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
