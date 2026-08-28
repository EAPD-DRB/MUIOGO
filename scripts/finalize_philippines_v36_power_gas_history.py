#!/usr/bin/env python3
"""Create the four-scenario validation and promotion qualification for v36."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import summarize_philippines_v36_power_gas_history as base_summary


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "WebAPP/DataStorage/.Philippines_v36-power-gas-history-candidate-20260827"
BASELINE = ROOT / "WebAPP/DataStorage/Philippines_v33"
RUNS = {
    "BASE": ("BASE_V36_POWER_GAS_HISTORY", "BASE_V33_GAS_DELIVERY"),
    "COAL_PHASEOUT": ("COAL_PHASEOUT_V36_POWER_GAS_HISTORY", "COAL_PHASEOUT_V33_GAS_DELIVERY"),
    "RE": ("RE_V36_POWER_GAS_HISTORY", "RE_V33_GAS_DELIVERY"),
    "EV": ("EV_V36_POWER_GAS_HISTORY", "EV_V33_GAS_DELIVERY"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    acceptance_path = CASE / "documentation/USER_ACCEPTANCE_V36_2026-08-28.json"
    acceptance = json.loads(acceptance_path.read_text())
    source_gate_path = CASE / "documentation/preflight_power_gas_history_v36.json"
    gate_adjustment_path = CASE / "documentation/preflight_gate_adjustment_v36.json"
    source_gate = json.loads(source_gate_path.read_text())
    gate_adjustment = json.loads(gate_adjustment_path.read_text())
    scenarios = {}
    all_checks: list[bool] = []

    for scenario, (run_name, baseline_name) in RUNS.items():
        run = CASE / "res" / run_name
        baseline_run = BASELINE / "res" / baseline_name
        optimization_path = run / "optimization_record.json"
        generation_path = run / "generation_matrix_report.json"
        generated_gate_path = run / "generated_power_gas_gate.json"
        optimization = json.loads(optimization_path.read_text())
        generation = json.loads(generation_path.read_text())
        generated_gate = json.loads(generated_gate_path.read_text())
        activity = base_summary.read_activity_by_mode(run / "csv")
        gross = base_summary.read_gross_generation(run / "csv")
        checks = {
            "optimal": str(optimization.get("status", "")).startswith("Optimal"),
            "one_optimizer_run": optimization.get("optimizer_runs") == 1,
            "runtime_gate_passed": optimization.get("runtime_acceptance_passed") is True,
            "generation_matrix_gate_passed": generation.get("status") == "passed"
            and generation.get("optimizer_runs") == 0,
            "generated_value_gate_passed": generated_gate.get("status") == "pass"
            and generated_gate.get("failure_count") == 0,
            "lp_hash_current": sha256(run / "lp.lp") == optimization.get("lp_sha256"),
            "results_hash_current": sha256(run / "results.txt") == optimization.get("results_sha256"),
            "generation_hashes_current": all(
                sha256(run / name) == digest for name, digest in generation["hashes"].items()
            ),
            "source_gate_hashes_current": generation["source_gate_hashes"]["equation_first"]
            == sha256(source_gate_path)
            and generation["source_gate_hashes"]["gate_adjustment"] == sha256(gate_adjustment_path),
            "scenario_identity_current": scenario in generation["active_scenarios"]
            and optimization.get("scenario") == scenario,
        }
        all_checks.extend(checks.values())
        scenarios[scenario] = {
            "run": run_name,
            "baseline_run": baseline_name,
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
                    "runtime_acceptance_passed",
                )
            },
            "matrix_dimensions": generation["matrix_dimensions"],
            "matrix_deltas": generation["matrix_deltas"],
            "historical_output": {
                str(year): {
                    "gross_grid_generation_pj": gross[year],
                    "legacy_gas_generation_pj": sum(
                        activity[(base_summary.GAS_TECH, year, mode)] for mode in (1, 2)
                    ),
                }
                for year in base_summary.YEARS
            },
            "checks": checks,
            "hashes": {
                "generation_matrix_report": sha256(generation_path),
                "generated_power_gas_gate": sha256(generated_gate_path),
                "optimization_record": sha256(optimization_path),
                "lp": optimization["lp_sha256"],
                "results": optimization["results_sha256"],
            },
        }

    expected_inventory = sorted(run_name for run_name, unused in RUNS.values())
    actual_inventory = sorted(path.name for path in (CASE / "res").iterdir() if path.is_dir())
    inventory_clean = actual_inventory == expected_inventory
    acceptance_valid = (
        acceptance.get("decision") == "accept_material_improvement_and_run_required_policy_scenarios"
        and acceptance.get("non_forcing_rule_unchanged") is True
    )
    source_gates_valid = (
        source_gate.get("status") == "pass_zero_solve"
        and source_gate.get("failure_count") == 0
        and gate_adjustment.get("status") == "pass_with_inherited_historical_stock_limitation"
        and gate_adjustment.get("failure_count") == 0
    )
    status = "pass" if all(all_checks) and inventory_clean and acceptance_valid and source_gates_valid else "fail"

    validation = {
        "schema": "philippines-v36-power-gas-four-scenario-validation-v1",
        "case": "Philippines_v36",
        "parent_case": "Philippines_v33",
        "status": status,
        "candidate_optimizer_runs": 4,
        "diagnostic_optimizer_runs": 0,
        "generation_only_rejected_threshold_attempts_outside_candidate": 1,
        "scenarios": scenarios,
        "run_inventory": {"expected": expected_inventory, "actual": actual_inventory, "clean": inventory_clean},
        "source_gates_valid": source_gates_valid,
        "user_acceptance": {
            "path": acceptance_path.relative_to(CASE).as_posix(),
            "sha256": sha256(acceptance_path),
            "valid": acceptance_valid,
            "scope": "historical-fit threshold only; non-forcing and all integrity gates remain mandatory",
        },
        "known_accepted_limitation": (
            "BASE materially improves gross generation and 2022-2024 gas dispatch but remains outside "
            "historical tolerances in specified years. Regional grid/transfer and plant-contract operating "
            "boundaries remain the required next correction."
        ),
    }
    validation_path = CASE / "documentation/power_gas_history_four_scenario_validation_v36.json"
    validation_path.write_text(json.dumps(validation, indent=2) + "\n")

    qualification = {
        "schema": "philippines-v36-power-gas-candidate-status-v1",
        "case": "Philippines_v36",
        "status": status,
        "promotion_allowed": status == "pass",
        "required_runs": expected_inventory,
        "actual_run_inventory": actual_inventory,
        "clean_run_inventory": inventory_clean,
        "all_scenarios_optimal": all(report["checks"]["optimal"] for report in scenarios.values()),
        "all_runtime_gates_passed": all(
            report["checks"]["runtime_gate_passed"] for report in scenarios.values()
        ),
        "all_hash_and_identity_gates_passed": all(all_checks),
        "source_gate": source_gate_path.relative_to(CASE).as_posix(),
        "validation": validation_path.relative_to(CASE).as_posix(),
        "user_acceptance": acceptance_path.relative_to(CASE).as_posix(),
        "accepted_calibration_limitation": acceptance["accepted_limitations"],
        "non_forcing": True,
        "policy_scenarios_required_and_completed": ["COAL_PHASEOUT", "RE", "EV"],
        "seal_required_before_promotion": True,
    }
    qualification_path = CASE / "documentation/power_gas_history_candidate_status_v36.json"
    qualification_path.write_text(json.dumps(qualification, indent=2) + "\n")
    print(json.dumps({"status": status, "promotion_allowed": qualification["promotion_allowed"], "objectives": {name: report["optimization"]["objective"] for name, report in scenarios.items()}}, indent=2))
    if status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
