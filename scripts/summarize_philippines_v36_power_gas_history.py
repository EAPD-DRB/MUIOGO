#!/usr/bin/env python3
"""Qualify the single solved Philippines v36 power/gas history candidate."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "WebAPP/DataStorage/.Philippines_v36-power-gas-history-candidate-20260827"
BASELINE = ROOT / "WebAPP/DataStorage/Philippines_v33"
RUN = "BASE_V36_POWER_GAS_HISTORY"
BASELINE_RUN = "BASE_V33_GAS_DELIVERY"
YEARS = range(2020, 2025)
GAS_TECH = "PHL_POW_CHP_NG_OLD"
DOE_GAS_GENERATION_PJ = {
    2020: 70.1892,
    2021: 68.6160,
    2022: 64.3824,
    2023: 60.0048,
    2024: 64.9692,
}
DOE_GRID_CONSUMPTION_GWH = {
    2020: 100274.720,
    2021: 106114.713,
    2022: 111515.669,
    2023: 118003.909,
    2024: 126940.827,
}
GROSS_ABSOLUTE_PERCENT_TOLERANCE = 5.0
GAS_ABSOLUTE_PERCENT_TOLERANCE = 15.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_activity_by_mode(csv_dir: Path) -> dict[tuple[str, int, int], float]:
    values: dict[tuple[str, int, int], float] = defaultdict(float)
    with (csv_dir / "TotalAnnualTechnologyActivityByMode.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            values[(row["t"], int(row["y"]), int(row["m"]))] += float(
                row["TotalAnnualTechnologyActivityByMode"]
            )
    return values


def read_gross_generation(csv_dir: Path) -> dict[int, float]:
    values: dict[int, float] = defaultdict(float)
    with (csv_dir / "ProductionByTechnologyByMode.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["f"] == "PHL_POW_ELE":
                values[int(row["y"])] += float(row["ProductionByTechnologyByMode"])
    return values


def pct_error(modeled: float, observed: float) -> float:
    return 100.0 * (modeled / observed - 1.0)


def solver_row(results: Path, marker: str) -> dict[str, float]:
    matches = [line for line in results.read_text(errors="replace").splitlines() if marker in line]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one solver row for {marker!r}, found {len(matches)}")
    fields = matches[0].split()
    return {"activity": float(fields[-2]), "dual": float(fields[-1])}


def top_activity_changes(candidate_csv: Path, baseline_csv: Path) -> list[dict[str, object]]:
    candidate = read_activity_by_mode(candidate_csv)
    baseline = read_activity_by_mode(baseline_csv)
    changes: list[dict[str, object]] = []
    technologies = sorted({key[0] for key in candidate} | {key[0] for key in baseline})
    for technology in technologies:
        annual = {
            str(year): sum(candidate[(technology, year, mode)] for mode in (1, 2))
            - sum(baseline[(technology, year, mode)] for mode in (1, 2))
            for year in YEARS
        }
        magnitude = sum(abs(value) for value in annual.values())
        if magnitude > 0.01:
            changes.append(
                {
                    "technology": technology,
                    "absolute_change_sum_2020_2024": magnitude,
                    "annual_change_pj": annual,
                }
            )
    return sorted(changes, key=lambda item: item["absolute_change_sum_2020_2024"], reverse=True)[:20]


def main() -> None:
    run = CASE / "res" / RUN
    baseline_run = BASELINE / "res" / BASELINE_RUN
    optimization = json.loads((run / "optimization_record.json").read_text())
    generation = json.loads((run / "generation_matrix_report.json").read_text())
    generated_gate = json.loads((run / "generated_power_gas_gate.json").read_text())
    source_gate = json.loads((CASE / "documentation/preflight_power_gas_history_v36.json").read_text())
    gate_adjustment = json.loads((CASE / "documentation/preflight_gate_adjustment_v36.json").read_text())
    source_audit = json.loads((CASE / "documentation/power_gas_history_source_change_v36.json").read_text())
    source_checks = {check["name"]: check for check in source_gate["checks"]}

    candidate_activity = read_activity_by_mode(run / "csv")
    baseline_activity = read_activity_by_mode(baseline_run / "csv")
    candidate_gross = read_gross_generation(run / "csv")
    baseline_gross = read_gross_generation(baseline_run / "csv")

    annual = {}
    gross_passes = []
    gas_passes = []
    for year in YEARS:
        observed_gross = DOE_GRID_CONSUMPTION_GWH[year] * 0.0036
        candidate_gas_modes = {
            str(mode): candidate_activity[(GAS_TECH, year, mode)] for mode in (1, 2)
        }
        baseline_gas = sum(baseline_activity[(GAS_TECH, year, mode)] for mode in (1, 2))
        candidate_gas = sum(candidate_gas_modes.values())
        gross_error = pct_error(candidate_gross[year], observed_gross)
        gas_error = pct_error(candidate_gas, DOE_GAS_GENERATION_PJ[year])
        gross_passes.append(abs(gross_error) <= GROSS_ABSOLUTE_PERCENT_TOLERANCE)
        gas_passes.append(abs(gas_error) <= GAS_ABSOLUTE_PERCENT_TOLERANCE)
        annual[str(year)] = {
            "observed_grid_gross_generation_pj": observed_gross,
            "v33_grid_gross_generation_pj": baseline_gross[year],
            "v36_grid_gross_generation_pj": candidate_gross[year],
            "v33_gross_percent_error": pct_error(baseline_gross[year], observed_gross),
            "v36_gross_percent_error": gross_error,
            "gross_absolute_error_improvement_percentage_points": abs(
                pct_error(baseline_gross[year], observed_gross)
            ) - abs(gross_error),
            "observed_gas_generation_pj": DOE_GAS_GENERATION_PJ[year],
            "v33_gas_generation_pj": baseline_gas,
            "v36_gas_generation_pj": candidate_gas,
            "v36_gas_generation_by_mode_pj": candidate_gas_modes,
            "v33_gas_percent_error": pct_error(baseline_gas, DOE_GAS_GENERATION_PJ[year]),
            "v36_gas_percent_error": gas_error,
            "gas_absolute_error_improvement_percentage_points": abs(
                pct_error(baseline_gas, DOE_GAS_GENERATION_PJ[year])
            ) - abs(gas_error),
        }

    integrity_checks = {
        "optimizer_optimal": str(optimization.get("status", "")).startswith("Optimal"),
        "one_candidate_optimizer_run": optimization.get("optimizer_runs") == 1,
        "runtime_gate_passed": optimization.get("runtime_acceptance_passed") is True,
        "application_generation_passed": generation.get("status") == "passed",
        "generated_value_gate_passed": generated_gate.get("status") == "pass"
        and generated_gate.get("failure_count") == 0,
        "source_preflight_passed": source_gate.get("status") == "pass_zero_solve"
        and source_gate.get("failure_count") == 0,
        "gate_adjustment_passed": gate_adjustment.get("status")
        == "pass_with_inherited_historical_stock_limitation",
        "generated_hashes_current": all(
            sha256(run / name) == digest for name, digest in generation["hashes"].items()
        ),
        "results_hash_current": sha256(run / "results.txt") == optimization["results_sha256"],
    }
    calibration_checks = {
        "gross_generation_within_5_percent_every_year": all(gross_passes),
        "gas_generation_within_15_percent_every_year": all(gas_passes),
        "2024_gas_generation_materially_improved": annual["2024"]["v36_gas_generation_pj"]
        > annual["2024"]["v33_gas_generation_pj"],
        "no_observed_dispatch_pin_or_floor": source_checks[
            "no_dispatch_floor_or_activity_pin"
        ]["status"] == "pass",
    }
    integrity_passed = all(integrity_checks.values())
    calibration_passed = all(calibration_checks.values())

    report = {
        "schema": "philippines-v36-power-gas-base-qualification-v1",
        "case": "Philippines_v36",
        "parent_case": "Philippines_v33",
        "candidate_directory": str(CASE),
        "status": "failed_base_calibration_qualification",
        "promotion_allowed": False,
        "reason": (
            "The source, matrix, solver and non-forcing integrity checks passed, but gas generation "
            "remains outside the declared validation tolerance in 2020, 2023 and 2024; 2024 reaches "
            "only 31.9347 PJ versus 64.9692 PJ observed."
        ),
        "observation_role": "benchmark_only",
        "integrity_passed": integrity_passed,
        "calibration_passed": calibration_passed,
        "integrity_checks": integrity_checks,
        "calibration_checks": calibration_checks,
        "tolerances": {
            "gross_generation_absolute_percent": GROSS_ABSOLUTE_PERCENT_TOLERANCE,
            "gas_generation_absolute_percent": GAS_ABSOLUTE_PERCENT_TOLERANCE,
        },
        "annual_comparison": annual,
        "optimization": {
            key: optimization[key]
            for key in (
                "status",
                "objective",
                "baseline_objective",
                "objective_change_percent",
                "solve_seconds",
                "baseline_runtime_seconds",
                "runtime_ratio_to_baseline",
            )
        },
        "matrix": generation["matrix_dimensions"],
        "matrix_deltas": generation["matrix_deltas"],
        "optimizer_run_inventory": {
            "candidate_base_runs": 1,
            "policy_runs": 0,
            "diagnostic_optimizer_runs": 0,
            "generation_only_diagnostics": 1,
        },
        "policy_scenarios": {
            "status": "not_run",
            "reason": "BASE failed the substantive historical calibration qualification; policy solves cannot cure that failure and would spend three unnecessary optimizer runs.",
        },
        "seal": {"status": "not_created", "reason": "Failed candidates are not sealed."},
        "promotion": {"status": "not_attempted", "reason": "BASE qualification failed."},
        "binding_diagnosis": {
            "2024_narrative": (
                "The discounted contract mode is below its activity cap and the market mode is unused. "
                "Domestic extraction binds while the sourced LNG option remains unused at its official "
                "2024 landed price; residual dispatch cannot be repaired by widening the contract cap "
                "or lowering LNG price without evidence."
            ),
            "2024_contract_mode": {
                "activity_pj": candidate_activity[(GAS_TECH, 2024, 1)],
                "upper_tranche_pj": next(
                    row["mode1_activity_upper_pj"]
                    for row in source_audit["contract_modes"] if row["year"] == 2024
                ),
                "upper_tranche_residual_pj": next(
                    row["mode1_activity_upper_pj"]
                    for row in source_audit["contract_modes"] if row["year"] == 2024
                ) - candidate_activity[(GAS_TECH, 2024, 1)],
                "constraint": solver_row(
                    run / "results.txt",
                    "LU1_TechnologyActivityByModeUL(RE1,PHL_POW_CHP_NG_OLD,1,2024)",
                ),
            },
            "2024_market_mode_activity_pj": candidate_activity[(GAS_TECH, 2024, 2)],
            "2024_domestic_extraction": {
                "source_cap_pj": 76.88193327412314,
                **solver_row(
                    run / "results.txt",
                    "AAC2_TotalAnnualTechnologyActivityUpperLimit(RE1,PHL_PRO_EXTR_NG,2024)",
                ),
            },
            "2024_lng_import": {
                "source_cap_pj": 395.2339200002194,
                **solver_row(
                    run / "results.txt",
                    "AAC2_TotalAnnualTechnologyActivityUpperLimit(RE1,PHL_PRO_IMP_NG,2024)",
                ),
            },
        },
        "next_equation_level_requirement": (
            "Represent the real regional/network and plant-contract operating boundary (Luzon load, "
            "inter-island transfer limits, and disclosed plant-level PPA/GSPA/LNG scheduling terms) "
            "before another optimizer run. A national copperplate cannot explain why costly Luzon gas "
            "ran while cheaper national substitutes appeared available."
        ),
        "top_base_activity_changes": top_activity_changes(run / "csv", baseline_run / "csv"),
    }
    path = CASE / "documentation/power_gas_history_base_qualification_v36.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(path), "status": report["status"], "annual": annual}, indent=2))
    if not integrity_passed:
        raise SystemExit("Integrity check failure while qualifying v36")


if __name__ == "__main__":
    main()
