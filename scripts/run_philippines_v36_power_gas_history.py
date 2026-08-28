#!/usr/bin/env python3
"""Generate/check and solve/export isolated Philippines v36 validation runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import run_philippines_v23_package1 as runner


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP/DataStorage"
DEFAULT_CASE = ".Philippines_v36-power-gas-history-candidate-20260827"
RUNS = {
    "BASE": "BASE_V36_POWER_GAS_HISTORY",
    "COAL_PHASEOUT": "COAL_PHASEOUT_V36_POWER_GAS_HISTORY",
    "RE": "RE_V36_POWER_GAS_HISTORY",
    "EV": "EV_V36_POWER_GAS_HISTORY",
}
BASELINE_CASE = STORAGE / "Philippines_v33"
BASELINES = {
    "BASE": (
        "BASE_V33_GAS_DELIVERY", 852438.33485986, 78.1788367909976,
        {"rows": 467075, "columns": 517844, "matrix_nonzeros": 8194641},
    ),
    "COAL_PHASEOUT": (
        "COAL_PHASEOUT_V33_GAS_DELIVERY", 873334.54788478, 124.49181858299562,
        {"rows": 467090, "columns": 517844, "matrix_nonzeros": 8194911},
    ),
    "RE": (
        "RE_V33_GAS_DELIVERY", 862660.13060768, 132.50547754199943,
        {"rows": 467075, "columns": 517844, "matrix_nonzeros": 8195151},
    ),
    "EV": (
        "EV_V33_GAS_DELIVERY", 828191.95783998, 148.53312570899288,
        {"rows": 467075, "columns": 517844, "matrix_nonzeros": 8194949},
    ),
}


def require_clean_source_gates(case: Path, scenario: str) -> dict[str, str]:
    paths = {
        "equation_first": case / "documentation/preflight_power_gas_history_v36.json",
        "gate_adjustment": case / "documentation/preflight_gate_adjustment_v36.json",
        "generic_active": case / f"documentation/generic_physical_gate_v36_{scenario}_active_formulation.json",
    }
    expected = {
        "equation_first": "pass_zero_solve",
        "gate_adjustment": "pass_with_inherited_historical_stock_limitation",
        "generic_active": "passed_no_deterministic_contradiction",
    }
    hashes = {}
    for name, path in paths.items():
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("status") != expected[name] or report.get("failure_count") != 0:
            raise RuntimeError(f"{name} gate failed: {path}")
        generation_runs = report.get("model_generation_runs", report.get("generation_runs"))
        if report.get("optimizer_runs") != 0 or generation_runs != 0:
            raise RuntimeError(f"{name} gate was not zero-solve and pre-generation")
        hashes[name] = runner.sha256(path)
    generated = case / "res" / RUNS[scenario] / "generated_power_gas_gate.json"
    if generated.is_file():
        report = json.loads(generated.read_text(encoding="utf-8"))
        if report.get("status") != "pass" or report.get("failure_count") != 0:
            raise RuntimeError(f"generated-value gate failed: {generated}")
        hashes["generated_power_gas"] = runner.sha256(generated)
    return hashes


def configure() -> None:
    runner.DEFAULT_CASE = DEFAULT_CASE
    runner.DEFAULT_RUN = RUNS["BASE"]
    runner.BASELINE_CASE = BASELINE_CASE
    runner.BASELINE_RUNS = BASELINES
    # Activating the physically identical market mode adds 680 columns
    # (0.1313%), 136 rows and 7,192 matrix nonzeros.  The 0.2% gate admits
    # that exact expected structure while remaining a tight corruption tripwire.
    runner.MAX_MATRIX_RATIO = 1.002
    runner.MAX_RUNTIME_RATIO = 2.0
    runner.OPTIMIZATION_PURPOSE = "Determine whether the sourced gross-to-sales balance, gas stock/efficiency, and capped contract economics reproduce plausible dispatch endogenously."
    runner.WHY_DETERMINISTIC_CHECKS_INSUFFICIENT = "Deterministic checks prove source identity and physical headroom, but only the coupled least-cost LP can determine endogenous generation, fuel allocation, objective value and runtime."
    runner.require_clean_source_gates = require_clean_source_gates

    original_create = runner.DataFile.createCaseRun

    def create_case_run(data_file, run_name, record):
        scenario = next(name for name, value in RUNS.items() if value == run_name)
        updated = dict(record)
        updated["CaseId"] = f"CS_PHL_V36_POWER_GAS_HISTORY_{scenario}"
        updated["Desc"] = f"Philippines v36 non-forcing power/gas history validation: {scenario}"
        return original_create(data_file, run_name, updated)

    runner.DataFile.createCaseRun = create_case_run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("generate-check", "solve-export"))
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--scenario", choices=tuple(RUNS), default="BASE")
    parser.add_argument("--run")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    configure()
    run = args.run or RUNS[args.scenario]
    if args.phase == "generate-check":
        runner.generate_check(args.case, run, args.scenario)
    else:
        runner.solve_export(args.case, run, args.timeout, args.scenario)


if __name__ == "__main__":
    main()
