#!/usr/bin/env python3
"""Generate/check and make bounded scenario attempts for vIS1.2."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import run_philippines_v23_package1 as runner


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP/DataStorage"
DEFAULT_CASE = ".Philippines_vIS12-candidate-20260828"
RUN = "BASE_VIS12_DIFFERENTIATED"
BASELINE_RUN = "BASE_VIS11_STABILIZED"
RUNS = {
    "BASE": RUN,
    "COAL_PHASEOUT": "COAL_PHASEOUT_VIS12_DIFFERENTIATED",
    "RE": "RE_VIS12_DIFFERENTIATED",
    "EV": "EV_VIS12_DIFFERENTIATED",
}
TIMEOUTS = {scenario: 360 for scenario in RUNS}


def require_clean_source_gates(case: Path, scenario: str) -> dict[str, str]:
    source = case / "documentation/preflight_island_power_vIS12.json"
    report = json.loads(source.read_text(encoding="utf-8"))
    if report.get("status") != "pass_zero_solve" or report.get("failure_count") != 0:
        raise RuntimeError("vIS1.2 source preflight is not a clean pass")
    if report.get("optimizer_runs") != 0 or report.get("generation_runs") != 0:
        raise RuntimeError("vIS1.2 source gate is not pre-generation and zero-solve")
    hashes = {"source_preflight": runner.sha256(source)}
    run = case / "res" / RUNS[scenario]
    if (run / "generation_matrix_report.json").is_file():
        generated = run / "generated_island_power_gate_vis12.json"
        if not generated.is_file():
            raise RuntimeError("generated vIS1.2 semantic gate is missing")
        result = json.loads(generated.read_text(encoding="utf-8"))
        if result.get("status") != "pass_generated_zero_solve" or result.get("failure_count") != 0:
            raise RuntimeError("generated vIS1.2 semantic gate is not a clean pass")
        hashes["generated_preflight"] = runner.sha256(generated)
    return hashes


def configure() -> None:
    runner.DEFAULT_CASE = DEFAULT_CASE
    runner.DEFAULT_RUN = RUN
    runner.BASELINE_CASE = STORAGE / "Philippines_v36"
    runner.BASELINE_RUNS = {
        "BASE": ("BASE_V36_POWER_GAS_HISTORY", 863976.44309006, 68.15735912499076,
                 {"rows": 467211, "columns": 518524, "matrix_nonzeros": 8201833}),
        "COAL_PHASEOUT": ("COAL_PHASEOUT_V36_POWER_GAS_HISTORY", 887217.82426329, 122.25675666700408,
                          {"rows": 467226, "columns": 518524, "matrix_nonzeros": 8202103}),
        "RE": ("RE_V36_POWER_GAS_HISTORY", 874666.81369337, 136.2588765410037,
               {"rows": 467211, "columns": 518524, "matrix_nonzeros": 8202343}),
        "EV": ("EV_V36_POWER_GAS_HISTORY", 840539.25824178, 160.31351324998832,
               {"rows": 467211, "columns": 518524, "matrix_nonzeros": 8202141}),
    }
    runner.MAX_MATRIX_RATIO = 2.0
    runner.MAX_RUNTIME_RATIO = None
    runner.OPTIMIZATION_PURPOSE = (
        "Test whether the sourced vIS1.2 grid-cost and renewable-resource differentiation, "
        "after deterministic feasibility gates, yields a simultaneous optimal scenario solution."
    )
    runner.WHY_DETERMINISTIC_CHECKS_INSUFFICIENT = (
        "The gates prove topology, exact demand/envelope accounting, renewable inputs, stock/vintage "
        "and every-timeslice constructive headroom, but only the coupled LP can establish simultaneous "
        "least-cost feasibility across all CLEWs balances and user-defined constraints."
    )
    runner.require_clean_source_gates = require_clean_source_gates
    original_create = runner.DataFile.createCaseRun

    def create_case_run(data_file, run_name, record):
        updated = dict(record)
        scenario = next((name for name, run in RUNS.items() if run == run_name), "UNKNOWN")
        updated["CaseId"] = f"CS_PHL_VIS12_DIFFERENTIATED_{scenario}"
        updated["Desc"] = f"Philippines vIS1.2 sourced spatial-cost/resource differentiation: {scenario}"
        return original_create(data_file, run_name, updated)

    runner.DataFile.createCaseRun = create_case_run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("generate-check", "solve-export"))
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--timeout", type=int, default=360)
    parser.add_argument("--scenario", choices=tuple(RUNS), default="BASE")
    parser.add_argument("--zero-solve-check-only", action="store_true")
    args = parser.parse_args()
    if args.timeout != TIMEOUTS[args.scenario]:
        raise RuntimeError(
            f"{args.scenario} has a fixed {TIMEOUTS[args.scenario]}-second deadline"
        )
    configure()
    if args.zero_solve_check_only:
        if args.phase != "generate-check":
            raise RuntimeError("--zero-solve-check-only is valid only for generate-check")
        runner.REQUIRE_BASE_OPTIMUM_FOR_POLICY = False
    run = RUNS[args.scenario]
    if args.phase == "generate-check":
        runner.generate_check(args.case, run, args.scenario)
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_philippines_vis1_generated.py"),
             "--case", str(STORAGE / args.case), "--run", run],
            check=True,
        )
    else:
        runner.solve_export(args.case, run, TIMEOUTS[args.scenario], args.scenario)


if __name__ == "__main__":
    main()
