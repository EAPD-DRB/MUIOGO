#!/usr/bin/env python3
"""Compare the validated Philippines v22 EV/truck candidate with canonical r9."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


SCENARIOS = ("BASE", "COAL_PHASEOUT", "RE", "EV")
CANDIDATE_RUNS = {s: f"EV_TRUCK_TURNOVER_V22_{s}" for s in SCENARIOS}
BASELINE_RUNS = {s: f"FIT_ACCOUNTING_V22_{s}" for s in SCENARIOS}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def objective(csv_dir: Path) -> float:
    return float(read_rows(csv_dir / "ObjectiveValue.csv")[0]["ObjectiveValue"])


def indexed_values(csv_dir: Path, filename: str, value: str) -> dict[tuple[str, int], float]:
    values: dict[tuple[str, int], float] = defaultdict(float)
    for row in read_rows(csv_dir / filename):
        values[(row["t"], int(row["y"]))] += float(row[value])
    return dict(values)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(
        (args.candidate / "data_sources/snapshots/ev_truck_turnover_build_manifest.json")
        .read_text(encoding="utf-8")
    )
    ev_technologies = [row["name"] for row in manifest["ev_technologies"]]
    truck_technologies = sorted(
        technology
        for technology in manifest["truck_envelopes"]
    )
    target_row = next(
        row for row in json.loads((args.candidate / "RYCn.json").read_text())["UCC"]["SC_huc7i"]
        if row["ConId"] == "CO_sdx29"
    )

    report: dict[str, object] = {
        "schema": "philippines-v22-ev-truck-turnover-comparison-v1",
        "baseline": str(args.baseline),
        "candidate": str(args.candidate),
        "ev_technologies": ev_technologies,
        "truck_technologies": truck_technologies,
        "scenarios": {},
    }

    for scenario in SCENARIOS:
        candidate_csv = args.candidate / "res" / CANDIDATE_RUNS[scenario] / "csv"
        baseline_csv = args.baseline / "res" / BASELINE_RUNS[scenario] / "csv"
        candidate_objective = objective(candidate_csv)
        baseline_objective = objective(baseline_csv)
        candidate_activity = indexed_values(
            candidate_csv,
            "TotalAnnualTechnologyActivityByMode.csv",
            "TotalAnnualTechnologyActivityByMode",
        )
        baseline_activity = indexed_values(
            baseline_csv,
            "TotalAnnualTechnologyActivityByMode.csv",
            "TotalAnnualTechnologyActivityByMode",
        )
        candidate_new_capacity = indexed_values(candidate_csv, "NewCapacity.csv", "NewCapacity")
        baseline_new_capacity = indexed_values(baseline_csv, "NewCapacity.csv", "NewCapacity")
        candidate_capacity = indexed_values(
            candidate_csv, "TotalCapacityAnnual.csv", "TotalCapacityAnnual"
        )

        all_activity_keys = set(candidate_activity) | set(baseline_activity)
        outside_trucks = []
        for key in all_activity_keys:
            technology, year = key
            if technology in truck_technologies:
                continue
            delta = candidate_activity.get(key, 0.0) - baseline_activity.get(key, 0.0)
            if abs(delta) > 1e-7:
                outside_trucks.append(
                    {"technology": technology, "year": year, "delta": delta}
                )
        outside_trucks.sort(key=lambda row: abs(row["delta"]), reverse=True)

        selected_years = (2020, 2021, 2022, 2023, 2024, 2025, 2026, 2030, 2040, 2053)
        truck_detail = {}
        for technology in truck_technologies:
            truck_detail[technology] = {
                str(year): {
                    "candidate_activity": candidate_activity.get((technology, year), 0.0),
                    "baseline_activity": baseline_activity.get((technology, year), 0.0),
                    "candidate_new_capacity": candidate_new_capacity.get((technology, year), 0.0),
                    "baseline_new_capacity": baseline_new_capacity.get((technology, year), 0.0),
                }
                for year in selected_years
            }

        ev_activity_by_year = {
            year: sum(candidate_activity.get((technology, year), 0.0) for technology in ev_technologies)
            for year in range(2020, 2054)
        }
        ev_target_residuals = {
            year: ev_activity_by_year[year] - float(target_row[str(year)])
            for year in range(2020, 2054)
        } if scenario == "EV" else {}
        active_ev_target_residuals = {
            year: residual
            for year, residual in ev_target_residuals.items()
            if year >= 2026
        }
        equality_duals = {
            int(row["y"]): float(row["UDC2_UserDefinedConstraintEquality"])
            for row in read_rows(candidate_csv / "UDC2_UserDefinedConstraintEquality.csv")
            if row["cn"] == "EV"
        }

        status = json.loads(
            (args.candidate / "res" / CANDIDATE_RUNS[scenario] / "optimization_record.json")
            .read_text(encoding="utf-8")
        )["status"]
        report["scenarios"][scenario] = {
            "solver_status": status,
            "objective": {
                "baseline": baseline_objective,
                "candidate": candidate_objective,
                "absolute_change": candidate_objective - baseline_objective,
                "percent_change": 100.0 * (candidate_objective - baseline_objective) / baseline_objective,
            },
            "candidate_ev_max_activity": max(abs(value) for value in ev_activity_by_year.values()),
            "candidate_ev_max_capacity": max(
                abs(candidate_capacity.get((technology, year), 0.0))
                for technology in ev_technologies
                for year in range(2020, 2054)
            ),
            "candidate_active_ev_target_max_abs_residual": (
                max(abs(value) for value in active_ev_target_residuals.values())
                if active_ev_target_residuals else None
            ),
            "candidate_ev_activity_before_target_start": {
                str(year): value for year, value in ev_activity_by_year.items()
                if year < 2026 and abs(value) > 1e-7
            },
            "candidate_ev_equality_duals_active_years": {
                str(year): equality_duals[year] for year in range(2026, 2054)
            },
            "candidate_ev_equality_dual_sign_counts": {
                "positive": sum(equality_duals[year] > 1e-8 for year in range(2026, 2054)),
                "negative": sum(equality_duals[year] < -1e-8 for year in range(2026, 2054)),
                "zero": sum(abs(equality_duals[year]) <= 1e-8 for year in range(2026, 2054)),
            },
            "candidate_ev_activity_by_year": {str(k): v for k, v in ev_activity_by_year.items()},
            "ev_target_residual_by_year": {str(k): v for k, v in ev_target_residuals.items()},
            "truck_selected_years": truck_detail,
            "largest_activity_changes_outside_trucks": outside_trucks[:25],
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        scenario: {
            "status": report["scenarios"][scenario]["solver_status"],
            "objective": report["scenarios"][scenario]["objective"],
            "ev_max_activity": report["scenarios"][scenario]["candidate_ev_max_activity"],
            "active_ev_target_max_abs_residual": report["scenarios"][scenario]["candidate_active_ev_target_max_abs_residual"],
        }
        for scenario in SCENARIOS
    }, indent=2))


if __name__ == "__main__":
    main()
