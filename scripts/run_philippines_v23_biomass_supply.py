#!/usr/bin/env python3
"""Generate/check and solve/export isolated Philippines v23 biomass runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import run_philippines_v23_package1 as runner


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
DEFAULT_CASE = ".Philippines_v23-biomass-supply-candidate-20260824"
RUNS = {
    "BASE": "BIOMASS_V23_BASE",
    "COAL_PHASEOUT": "BIOMASS_V23_COAL_PHASEOUT",
    "RE": "BIOMASS_V23_RE",
    "EV": "BIOMASS_V23_EV",
}
BASELINE_CASE = STORAGE / ".Philippines_v23-package1-candidate-20260824"
BASELINES = {
    "BASE": ("PACKAGE1_V23_BASE", 369951589.020571, 165.78136366699982,
             {"rows": 554873, "columns": 586648, "matrix_nonzeros": 8118754}),
    "COAL_PHASEOUT": ("PACKAGE1_V23_COAL_PHASEOUT", 369974408.9081208, 175.56098933400062,
                      {"rows": 554888, "columns": 586648, "matrix_nonzeros": 8119024}),
    "RE": ("PACKAGE1_V23_RE", 369965855.1230959, 274.87052233400027,
           {"rows": 554873, "columns": 586648, "matrix_nonzeros": 8119264}),
    "EV": ("PACKAGE1_V23_EV", 369936176.666302, 257.3222569999998,
           {"rows": 554873, "columns": 586648, "matrix_nonzeros": 8119062}),
}


def require_clean_source_gates(case: Path, scenario: str) -> dict[str, str]:
    generic_name = {
        "BASE": "biomass_generic_gate_base.json",
        "COAL_PHASEOUT": "biomass_generic_gate_coal_phaseout.json",
        "RE": "biomass_generic_gate_re.json",
        "EV": "biomass_generic_gate_ev.json",
    }[scenario]
    reports = {
        "generic": case / "documentation" / generic_name,
        "semantic": case / "documentation" / "biomass_specific_gate.json",
    }
    hashes = {}
    for name, path in reports.items():
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("failure_count") != 0 or not str(report.get("status", "")).startswith("pass"):
            raise RuntimeError(f"{name} source gate is not a clean pass: {path}")
        if report.get("optimizer_runs") != 0 or report.get("model_generation_runs") != 0:
            raise RuntimeError(f"{name} source gate was not pre-generation and zero-solve")
        hashes[name] = runner.sha256(path)
    return hashes


def configure():
    runner.DEFAULT_CASE = DEFAULT_CASE
    runner.DEFAULT_RUN = RUNS["BASE"]
    runner.BASELINE_CASE = BASELINE_CASE
    runner.BASELINE_RUNS = BASELINES
    # The minimal formulation adds one supply technology and no commodities;
    # retain a bounded matrix-growth tripwire.
    runner.MAX_MATRIX_RATIO = 1.10
    # Runtime ratios remain recorded, but the user accepted the measured
    # scenario-specific increase on 2026-08-25 because the corrected biomass
    # formulation changes the active policy problem. Optimality, not a fixed
    # historical wall-time ratio, is the promotion gate.
    runner.MAX_RUNTIME_RATIO = None
    runner.require_clean_source_gates = require_clean_source_gates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("generate-check", "solve-export"))
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--scenario", choices=tuple(RUNS), default="BASE")
    parser.add_argument("--run")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    configure()
    run = args.run or RUNS[args.scenario]
    if args.phase == "generate-check":
        runner.generate_check(args.case, run, args.scenario)
    else:
        runner.solve_export(args.case, run, args.timeout, args.scenario)


if __name__ == "__main__":
    main()
