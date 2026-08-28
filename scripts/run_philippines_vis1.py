#!/usr/bin/env python3
"""Generate/check and solve/export Philippines vIS1.1 with a BASE-only stop gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import run_philippines_v23_package1 as runner


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP/DataStorage"
DEFAULT_CASE = ".Philippines_vIS11-candidate-20260828"
RUNS = {
    "BASE": "BASE_VIS11_STABILIZED",
    "COAL_PHASEOUT": "COAL_PHASEOUT_VIS1_ISLAND_POWER",
    "RE": "RE_VIS1_ISLAND_POWER",
    "EV": "EV_VIS1_ISLAND_POWER",
}
BASELINES = {
    "BASE": ("BASE_V36_POWER_GAS_HISTORY", 863976.44309006, 68.1574, {"rows": 467211, "columns": 518524, "matrix_nonzeros": 8201833}),
    "COAL_PHASEOUT": ("COAL_PHASEOUT_V36_POWER_GAS_HISTORY", 887217.82426329, 122.25675666700408, {"rows": 467226, "columns": 518524, "matrix_nonzeros": 8202103}),
    "RE": ("RE_V36_POWER_GAS_HISTORY", 874666.81369337, 136.2588765410037, {"rows": 467211, "columns": 518524, "matrix_nonzeros": 8202343}),
    "EV": ("EV_V36_POWER_GAS_HISTORY", 840539.25824178, 160.31351324998832, {"rows": 467211, "columns": 518524, "matrix_nonzeros": 8202141}),
}


def require_clean_source_gates(case: Path, scenario: str) -> dict[str, str]:
    source = case / "documentation/preflight_island_power_vIS11.json"
    report = json.loads(source.read_text())
    if report.get("status") != "pass_zero_solve" or report.get("failure_count") != 0:
        raise RuntimeError("vIS1 source preflight is not a clean pass")
    if report.get("optimizer_runs") != 0 or report.get("generation_runs") != 0:
        raise RuntimeError("vIS1 source gate is not pre-generation and zero-solve")
    hashes = {"source_preflight": runner.sha256(source)}
    run = case / "res" / RUNS[scenario]
    if (run / "generation_matrix_report.json").is_file():
        generated = run / "generated_island_power_gate_vis11.json"
        if not generated.is_file(): raise RuntimeError("generated vIS1 semantic gate is missing")
        result = json.loads(generated.read_text())
        if result.get("status") != "pass_generated_zero_solve" or result.get("failure_count") != 0:
            raise RuntimeError("generated vIS1 semantic gate is not a clean pass")
        hashes["generated_preflight"] = runner.sha256(generated)
    return hashes


def configure() -> None:
    runner.DEFAULT_CASE = DEFAULT_CASE
    runner.DEFAULT_RUN = RUNS["BASE"]
    runner.BASELINE_CASE = STORAGE / "Philippines_v36"
    runner.BASELINE_RUNS = BASELINES
    runner.MAX_MATRIX_RATIO = 2.0
    runner.MAX_RUNTIME_RATIO = None
    runner.OPTIMIZATION_PURPOSE = "Establish coupled BASE feasibility and optimality of the stabilized vIS1.1 island split after full source/generated deterministic gates passed."
    runner.WHY_DETERMINISTIC_CHECKS_INSUFFICIENT = "The gate proves topology, conservation, stock/vintage envelopes and demand headroom, but only the coupled LP can establish simultaneous least-cost feasibility across all commodities and constraints."
    runner.require_clean_source_gates = require_clean_source_gates
    original_create = runner.DataFile.createCaseRun
    def create_case_run(data_file, run_name, record):
        scenario = next(k for k, v in RUNS.items() if v == run_name)
        updated = dict(record)
        updated["CaseId"] = f"CS_PHL_VIS11_STABILIZED_{scenario}"
        updated["Desc"] = f"Philippines vIS1.1 stabilized island-power validation: {scenario}"
        return original_create(data_file, run_name, updated)
    runner.DataFile.createCaseRun = create_case_run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("generate-check", "solve-export"))
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--scenario", choices=tuple(RUNS), default="BASE")
    parser.add_argument("--timeout", type=int, default=360)
    args = parser.parse_args()
    configure()
    run = RUNS[args.scenario]
    if args.phase == "generate-check": runner.generate_check(args.case, run, args.scenario)
    else: runner.solve_export(args.case, run, args.timeout, args.scenario)


if __name__ == "__main__":
    main()
