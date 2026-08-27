#!/usr/bin/env python3
"""Summarize and qualify the solved Philippines v33 gas-delivery candidate."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "WebAPP/DataStorage/.Philippines_v33-gas-delivery-candidate-20260827"
BASELINE = ROOT / "WebAPP/DataStorage/Philippines_v32"
RUNS = {
    "BASE": ("BASE_V33_GAS_DELIVERY", "BASE_V32_RICE_YIELD"),
    "COAL_PHASEOUT": ("COAL_PHASEOUT_V33_GAS_DELIVERY", "COAL_PHASEOUT_V32_RICE_YIELD"),
    "RE": ("RE_V33_GAS_DELIVERY", "RE_V32_RICE_YIELD"),
    "EV": ("EV_V33_GAS_DELIVERY", "EV_V32_RICE_YIELD"),
}
YEARS = range(2020, 2025)
NONPOWER_GAS = {
    "PHL_AGR_HEAT_NG", "PHL_INDU_OTHHPH_NG", "PHL_INDU_OTHHPH_NG_CCS",
    "PHL_INDU_OTHLPH_NG", "PHL_POW_BH2_NG", "PHL_POW_GH2_NG",
    "PHL_SER_HEAT_NG", "PHL_TRA_23WHEEL_NG", "PHL_TRA_BUS_NG",
    "PHL_TRA_CAR_NG", "PHL_TRA_TRUH_NG", "PHL_TRA_TRUL_NG",
    "PHL_TRA_VAN_NG", "PHL_HOU_COOK_NG",
}
DOE_GAS_GENERATION = {
    2020: 70.1892, 2021: 68.616, 2022: 64.3824, 2023: 60.0048, 2024: 64.9692,
}
DOE_GROSS_2024 = 456.988


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_activity(csv_dir: Path) -> dict[tuple[str, int], float]:
    values: dict[tuple[str, int], float] = defaultdict(float)
    with (csv_dir / "TotalAnnualTechnologyActivityByMode.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            values[(row["t"], int(row["y"]))] += float(row["TotalAnnualTechnologyActivityByMode"])
    return values


def read_gas_use(csv_dir: Path) -> dict[tuple[str, int], float]:
    values: dict[tuple[str, int], float] = defaultdict(float)
    with (csv_dir / "UseByTechnologyByMode.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["f"] == "PHL_PRO_NG":
                values[(row["t"], int(row["y"]))] += float(row["UseByTechnologyByMode"])
    return values


def read_gross_generation(csv_dir: Path) -> dict[int, float]:
    values: dict[int, float] = defaultdict(float)
    with (csv_dir / "ProductionByTechnologyByMode.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["f"] == "PHL_POW_ELE":
                values[int(row["y"])] += float(row["ProductionByTechnologyByMode"])
    return values


def extraction_duals(results: Path) -> dict[str, float]:
    values = {}
    for line in results.read_text(errors="replace").splitlines():
        marker = "AAC2_TotalAnnualTechnologyActivityUpperLimit(RE1,PHL_PRO_EXTR_NG,"
        if marker not in line:
            continue
        year = line.split(marker, 1)[1].split(")", 1)[0]
        fields = line.split()
        values[year] = float(fields[-1])
    return values


def metrics(run: Path) -> dict[str, object]:
    csv_dir = run / "csv"
    activity = read_activity(csv_dir)
    gas_use = read_gas_use(csv_dir)
    gross = read_gross_generation(csv_dir)
    return {
        str(year): {
            "legacy_gas_generation_pj": activity[("PHL_POW_CHP_NG_OLD", year)],
            "nonpower_processed_gas_use_pj": sum(gas_use[(tech, year)] for tech in NONPOWER_GAS),
            "gas_extraction_activity_pj": activity[("PHL_PRO_EXTR_NG", year)],
            "gas_import_activity_pj": activity[("PHL_PRO_IMP_NG", year)],
            "gross_grid_generation_pj": gross[year],
        }
        for year in YEARS
    }


def top_activity_changes(candidate_run: Path, baseline_run: Path) -> list[dict[str, object]]:
    candidate = read_activity(candidate_run / "csv")
    baseline = read_activity(baseline_run / "csv")
    changes = []
    for technology in sorted({key[0] for key in candidate} | {key[0] for key in baseline}):
        annual = {str(year): candidate[(technology, year)] - baseline[(technology, year)] for year in YEARS}
        magnitude = sum(abs(value) for value in annual.values())
        if magnitude > 0.01:
            changes.append({"technology": technology, "absolute_change_sum_2020_2024": magnitude, "annual_change": annual})
    return sorted(changes, key=lambda item: item["absolute_change_sum_2020_2024"], reverse=True)[:30]


def main() -> None:
    ryt = json.loads((CASE / "RYT.json").read_text())
    gen = json.loads((CASE / "genData.json").read_text())
    extraction_id = next(row["TechId"] for row in gen["osy-tech"] if row["Tech"] == "PHL_PRO_EXTR_NG")
    extraction_cap = next(row for row in ryt["TAU"]["SC_0"] if row["TechId"] == extraction_id)

    scenario_reports = {}
    all_checks = []
    for scenario, (candidate_name, baseline_name) in RUNS.items():
        candidate_run = CASE / "res" / candidate_name
        baseline_run = BASELINE / "res" / baseline_name
        optimization = json.loads((candidate_run / "optimization_record.json").read_text())
        generation = json.loads((candidate_run / "generation_matrix_report.json").read_text())
        candidate_metrics = metrics(candidate_run)
        baseline_metrics = metrics(baseline_run)
        residuals = {
            str(year): float(extraction_cap[str(year)]) - candidate_metrics[str(year)]["gas_extraction_activity_pj"]
            for year in YEARS
        }
        checks = {
            "optimal": str(optimization.get("status", "")).startswith("Optimal"),
            "promotion_allowed": optimization.get("promotion_allowed") is True,
            "runtime_gate": optimization.get("runtime_acceptance_passed") is True,
            "matrix_exact": all(value == 0 for value in generation["matrix_deltas"].values()),
            "generated_hashes_current": all(
                sha256(candidate_run / name) == digest for name, digest in generation["hashes"].items()
            ),
            "results_hash_current": sha256(candidate_run / "results.txt") == optimization["results_sha256"],
        }
        all_checks.extend(checks.values())
        scenario_reports[scenario] = {
            "candidate_run": candidate_name, "baseline_run": baseline_name,
            "optimization": {
                key: optimization[key] for key in (
                    "status", "objective", "baseline_objective", "objective_change",
                    "objective_change_percent", "solve_seconds", "baseline_runtime_seconds",
                    "runtime_ratio_to_baseline", "runtime_acceptance_passed",
                )
            },
            "matrix": generation["matrix_dimensions"], "matrix_deltas": generation["matrix_deltas"],
            "candidate_metrics": candidate_metrics, "baseline_metrics": baseline_metrics,
            "extraction_cap_residual_pj": residuals,
            "extraction_cap_dual": extraction_duals(candidate_run / "results.txt"),
            "checks": checks,
            "artifact_timestamps_ns": {
                name: (candidate_run / name).stat().st_mtime_ns
                for name in ("data.txt", "data_processed.txt", "lp.lp", "cbc.log", "results.txt", "optimization_record.json")
            },
        }

    base = scenario_reports["BASE"]
    base_candidate = base["candidate_metrics"]
    base_baseline = base["baseline_metrics"]
    validation = {
        "case": "Philippines_v33", "parent_case": "Philippines_v32",
        "status": "pass" if all(all_checks) else "fail",
        "candidate_optimizer_runs": 4,
        "diagnostic_optimizer_runs_outside_candidate": 2,
        "diagnostic_directories": [
            ".Philippines_v33-gas-delivery-diagnostic-20260827",
            ".Philippines_v33-gas-delivery-diagnostic2-20260827",
        ],
        "scenarios": scenario_reports,
        "base_benchmark": {
            str(year): {
                "doe_gas_generation_pj": DOE_GAS_GENERATION[year],
                "v32_gas_generation_pj": base_baseline[str(year)]["legacy_gas_generation_pj"],
                "v33_gas_generation_pj": base_candidate[str(year)]["legacy_gas_generation_pj"],
                "v33_percent_of_observed": 100 * base_candidate[str(year)]["legacy_gas_generation_pj"] / DOE_GAS_GENERATION[year],
            }
            for year in YEARS
        },
        "base_effect": {
            "nonpower_gas_reduction_percent_2023": 100 * (
                1 - base_candidate["2023"]["nonpower_processed_gas_use_pj"] / base_baseline["2023"]["nonpower_processed_gas_use_pj"]
            ),
            "nonpower_gas_reduction_percent_2024": 100 * (
                1 - base_candidate["2024"]["nonpower_processed_gas_use_pj"] / base_baseline["2024"]["nonpower_processed_gas_use_pj"]
            ),
            "gas_import_reduction_pj_2023": base_baseline["2023"]["gas_import_activity_pj"] - base_candidate["2023"]["gas_import_activity_pj"],
            "gas_import_reduction_pj_2024": base_baseline["2024"]["gas_import_activity_pj"] - base_candidate["2024"]["gas_import_activity_pj"],
            "gross_generation_2024_pj": base_candidate["2024"]["gross_grid_generation_pj"],
            "doe_gross_generation_2024_pj": DOE_GROSS_2024,
            "gross_generation_gap_2024_pj": DOE_GROSS_2024 - base_candidate["2024"]["gross_grid_generation_pj"],
            "gross_generation_gap_2024_percent": 100 * (1 - base_candidate["2024"]["gross_grid_generation_pj"] / DOE_GROSS_2024),
        },
        "top_base_activity_changes": top_activity_changes(
            CASE / "res" / RUNS["BASE"][0], BASELINE / "res" / RUNS["BASE"][1]
        ),
        "limitations": [
            "The 8.2 MUSD/PJ_input adder is a conservative proxy, not a Philippines route-specific tariff.",
            "Embedding delivery cost in conversion VC cannot represent endogenous gas-network investment.",
            "Non-power gas remains endogenous and is reduced, not prohibited.",
            "Electricity demand and power-plant own-use are unchanged; DOE gross generation remains validation-only.",
            "The 2024 gas/coal split remains structurally unresolved in an annual least-cost model.",
        ],
    }
    report_path = CASE / "documentation/gas_delivery_four_scenario_validation_v33.json"
    report_path.write_text(json.dumps(validation, indent=2) + "\n")

    inventory = sorted(path.name for path in (CASE / "res").iterdir() if path.is_dir())
    expected_inventory = sorted(candidate for candidate, unused in RUNS.values())
    qualification = {
        "case": "Philippines_v33", "status": validation["status"],
        "promotion_allowed": validation["status"] == "pass" and inventory == expected_inventory,
        "required_runs": expected_inventory, "actual_run_inventory": inventory,
        "clean_run_inventory": inventory == expected_inventory,
        "all_scenarios_optimal": all(
            report["checks"]["optimal"] and report["checks"]["promotion_allowed"]
            for report in scenario_reports.values()
        ),
        "source_gate": "documentation/preflight_gas_delivery_v33.json",
        "validation": report_path.relative_to(CASE).as_posix(),
        "known_limitations": validation["limitations"],
        "diagnostic_runs_excluded_from_candidate": validation["diagnostic_directories"],
    }
    qualification_path = CASE / "documentation/gas_delivery_candidate_status_v33.json"
    qualification_path.write_text(json.dumps(qualification, indent=2) + "\n")
    print(json.dumps({"validation_status": validation["status"], "qualification": qualification}, indent=2))
    if not qualification["promotion_allowed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
