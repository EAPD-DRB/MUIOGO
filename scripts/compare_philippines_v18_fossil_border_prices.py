#!/usr/bin/env python3
"""Compare the accepted PHL v18 fossil-resource run with the price candidate."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STORAGE = REPO / "WebAPP" / "DataStorage"
BASELINE = STORAGE / ".Philippines_v18-power-investment-20260817" / "res" / "TOMORROWLAND"
CANDIDATE = STORAGE / ".Philippines_v18-fossil-border-price-candidate" / "res" / "TOMORROWLAND"
ACTIVITY_FILE = "TotalAnnualTechnologyActivityByMode.csv"
DIRECT_FOSSIL = {
    "PHL_PRO_EXTR_COAL",
    "PHL_PRO_SUP_COAL_DOM",
    "PHL_PRO_EXP_COAL",
    "PHL_PRO_IMP_COAL",
    "PHL_PRO_EXTR_OIL",
    "PHL_PRO_SUP_OIL_DOM",
    "PHL_PRO_EXP_OIL",
    "PHL_PRO_IMP_OIL",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], dict[tuple[str, ...], float]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        values = {tuple(row[:-1]): float(row[-1]) for row in reader}
    return header, values


def activity(run: Path) -> dict[tuple[str, str, str, str], float]:
    _, values = read_csv(run / "csv" / ACTIVITY_FILE)
    return values


def by_technology_difference(
    baseline: dict[tuple[str, str, str, str], float],
    candidate: dict[tuple[str, str, str, str], float],
) -> list[dict[str, float | str]]:
    totals: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for key in baseline.keys() | candidate.keys():
        technology = key[1]
        totals[technology][0] += baseline.get(key, 0.0)
        totals[technology][1] += candidate.get(key, 0.0)
    rows = [
        {
            "technology": technology,
            "baseline": values[0],
            "candidate": values[1],
            "change": values[1] - values[0],
        }
        for technology, values in totals.items()
        if abs(values[1] - values[0]) > 1e-6
    ]
    return sorted(rows, key=lambda row: abs(float(row["change"])), reverse=True)


def series(
    values: dict[tuple[str, str, str, str], float], technology: str
) -> dict[str, float]:
    result: dict[str, float] = defaultdict(float)
    for (_, tech, _mode, year), value in values.items():
        if tech == technology:
            result[year] += value
    return dict(sorted(result.items()))


def objective(run: Path) -> float:
    first_line = (run / "results.txt").read_text(encoding="utf-8").splitlines()[0]
    return float(first_line.rsplit(" ", 1)[-1])


def solve_record(run: Path) -> dict[str, float | int | str]:
    log_path = run / "candidate_cbc.log"
    if not log_path.is_file():
        log_path = run / "cbc.log"
    log = log_path.read_text(encoding="utf-8")
    match = re.search(r"Optimal objective\s+([-+0-9.eE]+)\s+-\s+(\d+) iterations", log)
    wall = re.search(r"Wallclock seconds\):\s+([0-9.]+)", log)
    presolve = re.search(
        r"Presolve\s+(\d+) \([^)]*\) rows,\s+(\d+) \([^)]*\) columns and\s+(\d+)", log
    )
    if not (match and wall and presolve):
        raise RuntimeError(f"Could not parse solve log {run}")
    return {
        "status": "optimal",
        "objective_from_results": objective(run),
        "iterations": int(match.group(2)),
        "cbc_wall_seconds": float(wall.group(1)),
        "presolved_rows": int(presolve.group(1)),
        "presolved_columns": int(presolve.group(2)),
        "presolved_nonzeros": int(presolve.group(3)),
    }


def emissions(run: Path) -> dict[tuple[str, str], float]:
    _, values = read_csv(run / "csv" / "AnnualTechnologyEmission.csv")
    totals: dict[tuple[str, str], float] = defaultdict(float)
    for (_region, _technology, emission, year), value in values.items():
        totals[(emission, year)] += value
    return totals


def technology_year_values(run: Path, filename: str) -> dict[tuple[str, str], float]:
    _, values = read_csv(run / "csv" / filename)
    totals: dict[tuple[str, str], float] = defaultdict(float)
    for (_region, technology, year), value in values.items():
        totals[(technology, year)] += value
    return totals


def largest_key_changes(
    baseline: dict[tuple[str, str], float],
    candidate: dict[tuple[str, str], float],
    limit: int = 25,
) -> list[dict[str, float | str]]:
    rows = [
        {
            "technology": key[0],
            "year": key[1],
            "baseline": baseline.get(key, 0.0),
            "candidate": candidate.get(key, 0.0),
            "change": candidate.get(key, 0.0) - baseline.get(key, 0.0),
        }
        for key in baseline.keys() | candidate.keys()
        if abs(candidate.get(key, 0.0) - baseline.get(key, 0.0)) > 1e-6
    ]
    return sorted(rows, key=lambda row: abs(float(row["change"])), reverse=True)[:limit]


def main() -> None:
    base = activity(BASELINE)
    cand = activity(CANDIDATE)
    tech_differences = by_technology_difference(base, cand)
    histories = {}
    for technology in sorted(DIRECT_FOSSIL):
        base_series = series(base, technology)
        cand_series = series(cand, technology)
        histories[technology] = {
            year: {
                "baseline": base_series.get(year, 0.0),
                "candidate": cand_series.get(year, 0.0),
                "change": cand_series.get(year, 0.0) - base_series.get(year, 0.0),
            }
            for year in map(str, range(2020, 2028))
        }

    branch_errors = {}
    for fuel in ("COAL", "OIL"):
        extraction = series(cand, f"PHL_PRO_EXTR_{fuel}")
        domestic = series(cand, f"PHL_PRO_SUP_{fuel}_DOM")
        exports = series(cand, f"PHL_PRO_EXP_{fuel}")
        branch_errors[fuel.lower()] = max(
            abs(extraction.get(year, 0.0) - domestic.get(year, 0.0) - exports.get(year, 0.0))
            for year in set(extraction) | set(domestic) | set(exports)
        )

    base_emissions = emissions(BASELINE)
    cand_emissions = emissions(CANDIDATE)
    emissions_delta = {}
    for emission in sorted({key[0] for key in base_emissions.keys() | cand_emissions.keys()}):
        baseline_total = sum(value for (name, _year), value in base_emissions.items() if name == emission)
        candidate_total = sum(value for (name, _year), value in cand_emissions.items() if name == emission)
        emissions_delta[emission] = {
            "baseline": baseline_total,
            "candidate": candidate_total,
            "change": candidate_total - baseline_total,
        }

    capacity_changes = {}
    for filename in ("NewCapacity.csv", "TotalCapacityAnnual.csv"):
        base_capacity = technology_year_values(BASELINE, filename)
        cand_capacity = technology_year_values(CANDIDATE, filename)
        capacity_changes[filename.removesuffix(".csv")] = {
            "changed_cells": sum(
                1
                for key in base_capacity.keys() | cand_capacity.keys()
                if abs(cand_capacity.get(key, 0.0) - base_capacity.get(key, 0.0)) > 1e-6
            ),
            "largest_changes": largest_key_changes(base_capacity, cand_capacity),
        }

    baseline_objective = objective(BASELINE)
    candidate_objective = objective(CANDIDATE)
    report = {
        "baseline": solve_record(BASELINE),
        "candidate": solve_record(CANDIDATE),
        "objective_change": candidate_objective - baseline_objective,
        "objective_change_percent": 100 * (candidate_objective - baseline_objective) / baseline_objective,
        "candidate_hashes": {
            name: sha256(CANDIDATE / name)
            for name in ("data.txt", "data_processed.txt", "lp.lp", "results.txt")
        },
        "direct_fossil_activity_2020_2027_pj": histories,
        "candidate_branch_balance_max_abs_error_pj": branch_errors,
        "candidate_total_exports_pj": {
            fuel.lower(): sum(series(cand, f"PHL_PRO_EXP_{fuel}").values())
            for fuel in ("COAL", "OIL")
        },
        "candidate_total_extraction_pj": {
            fuel.lower(): sum(series(cand, f"PHL_PRO_EXTR_{fuel}").values())
            for fuel in ("COAL", "OIL")
        },
        "changed_activity_cells": sum(
            1 for key in base.keys() | cand.keys() if abs(cand.get(key, 0.0) - base.get(key, 0.0)) > 1e-6
        ),
        "changed_activity_cells_outside_direct_fossil": sum(
            1
            for key in base.keys() | cand.keys()
            if key[1] not in DIRECT_FOSSIL and abs(cand.get(key, 0.0) - base.get(key, 0.0)) > 1e-6
        ),
        "largest_model_period_activity_changes": tech_differences[:25],
        "capacity_changes": capacity_changes,
        "model_period_emissions": emissions_delta,
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
