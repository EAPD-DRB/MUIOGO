#!/usr/bin/env python3
"""Generate/check and solve/export isolated Philippines v32 rice-yield runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import run_philippines_v23_package1 as runner


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
DEFAULT_CASE = ".Philippines_v32-rice-yield-candidate-20260827"
RUNS = {
    "BASE": "BASE_V32_RICE_YIELD",
    "COAL_PHASEOUT": "COAL_PHASEOUT_V32_RICE_YIELD",
    "RE": "RE_V32_RICE_YIELD",
    "EV": "EV_V32_RICE_YIELD",
}
BASELINE_CASE = STORAGE / "Philippines_v31"
BASELINES = {
    "BASE": (
        "BASE_V31",
        816774.34133720,
        74.22,
        {"rows": 467075, "columns": 517844, "matrix_nonzeros": 8194641},
    ),
    "COAL_PHASEOUT": (
        "COAL_PHASEOUT_V31",
        832681.23504832,
        99.06,
        {"rows": 467090, "columns": 517844, "matrix_nonzeros": 8194911},
    ),
    "RE": (
        "RE_V31",
        826050.65517129,
        114.53,
        {"rows": 467075, "columns": 517844, "matrix_nonzeros": 8195151},
    ),
    "EV": (
        "EV_V31",
        793751.53299466,
        113.76,
        {"rows": 467075, "columns": 517844, "matrix_nonzeros": 8194949},
    ),
}


def require_clean_source_gates(case: Path, unused_scenario: str) -> dict[str, str]:
    path = case / "documentation/preflight_rice_spatial_yield_v32.json"
    report = json.loads(path.read_text())
    if report.get("status") != "pass" or report.get("optimizer_runs") != 0:
        raise RuntimeError(f"rice source gate is not a clean zero-solve pass: {path}")
    return {"rice_spatial_yield": runner.sha256(path)}


def configure() -> None:
    runner.DEFAULT_CASE = DEFAULT_CASE
    runner.DEFAULT_RUN = RUNS["BASE"]
    runner.BASELINE_CASE = BASELINE_CASE
    runner.BASELINE_RUNS = BASELINES
    runner.MAX_MATRIX_RATIO = 1.000001
    runner.MAX_RUNTIME_RATIO = 2.0
    runner.require_clean_source_gates = require_clean_source_gates

    original_create = runner.DataFile.createCaseRun

    def create_case_run(data_file, run_name, record):
        scenario = next(name for name, value in RUNS.items() if value == run_name)
        updated = dict(record)
        updated["CaseId"] = f"CS_PHL_V32_RICE_YIELD_{scenario}"
        updated["Desc"] = (
            f"Philippines v32 spatial achieved-rice-yield validation: {scenario}"
        )
        return original_create(data_file, run_name, updated)

    runner.DataFile.createCaseRun = create_case_run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("generate-check", "solve-export"))
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--scenario", choices=tuple(RUNS), default="BASE")
    parser.add_argument("--run")
    parser.add_argument("--timeout", type=int, default=160)
    args = parser.parse_args()
    configure()
    run = args.run or RUNS[args.scenario]
    if args.phase == "generate-check":
        runner.generate_check(args.case, run, args.scenario)
    else:
        runner.solve_export(args.case, run, args.timeout, args.scenario)


if __name__ == "__main__":
    main()
