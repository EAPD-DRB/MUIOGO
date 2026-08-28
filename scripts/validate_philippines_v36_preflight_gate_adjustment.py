#!/usr/bin/env python3
"""Qualify the generic pre-flight gate for Philippines v36 launch use."""

from __future__ import annotations

import json
from pathlib import Path

import validate_osemosys_physical_gate as generic


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "WebAPP/DataStorage/Philippines_v33"
CANDIDATE = ROOT / "WebAPP/DataStorage/.Philippines_v36-power-gas-history-candidate-20260827"
SCENARIOS = {
    "BASE": "SC_0",
    "COAL_PHASEOUT": "SC_3hgjb",
    "RE": "SC_w03qj",
    "EV": "SC_huc7i",
}


def signature(report: dict) -> list[tuple]:
    return sorted(
        (
            row.get("kind"), row.get("year"), row.get("timeslice"),
            row.get("commodity_id"), row.get("technology_id"), row.get("constraint_id"),
        )
        for row in report.get("failures", [])
    )


def main() -> None:
    source = json.loads((CANDIDATE / "documentation/preflight_power_gas_history_v36.json").read_text())
    active = {
        name: json.loads(
            (CANDIDATE / f"documentation/generic_physical_gate_v36_{name}_active_formulation.json").read_text()
        )
        for name in SCENARIOS
    }
    strict = {
        name: json.loads(
            (CANDIDATE / f"documentation/generic_physical_gate_v36_{name}.json").read_text()
        )
        for name in SCENARIOS
    }
    baseline_strict = generic.validate_case(
        BASELINE, scenario="SC_0", historical_through=2024,
    )
    checks = {
        "candidate_specific_equation_gate": (
            source.get("status") == "pass_zero_solve" and source.get("failure_count") == 0
        ),
        "all_active_formulation_gates_pass": all(
            report.get("status") == "passed_no_deterministic_contradiction"
            and report.get("failure_count") == 0
            for report in active.values()
        ),
        "strict_base_failure_signature_is_inherited": (
            signature(strict["BASE"]) == signature(baseline_strict)
            and len(signature(strict["BASE"])) == 314
        ),
        "strict_variant_failures_are_inherited_subset": all(
            set(signature(report)).issubset(set(signature(baseline_strict)))
            for report in strict.values()
        ),
        "zero_optimizer_and_generation_runs": all(
            report.get("optimizer_runs") == 0 and report.get("model_generation_runs") == 0
            for report in list(active.values()) + list(strict.values()) + [baseline_strict]
        ),
    }
    report = {
        "schema": "philippines-v36-preflight-gate-adjustment-v1",
        "status": "pass_with_inherited_historical_stock_limitation" if all(checks.values()) else "fail",
        "failure_count": sum(not value for value in checks.values()),
        "optimizer_runs": 0,
        "model_generation_runs": 0,
        "launch_rule": "Require the candidate-specific equation gate and the generic active-formulation gate. Retain --historical-through 2024 as an advisory stock-audit report, not a launch blocker, until inherited historical replacement investment is reclassified as commissioned residual stock.",
        "reason": "The strict option intentionally removes finite endogenous investment in 2020-2024. Sealed v33 is optimal only because the active formulation permits such investment (for example, PHL_SER_HEAT_BIOM adds 10.5545 in 2021 and 4.0444 in 2022). Therefore the 310-314 heat-service shortfalls are not contradictions in the active LP; BASE is identical to v33 and policy failures are subsets of the inherited BASE signature.",
        "scope_safety": "The v36 candidate-specific gate separately proves every changed electricity/gas stock, efficiency, resource and contract equation over the historical period.",
        "checks": checks,
        "strict_failure_counts": {name: report["failure_count"] for name, report in strict.items()},
        "active_statuses": {name: report["status"] for name, report in active.items()},
        "baseline_strict_failure_count": baseline_strict["failure_count"],
    }
    path = CANDIDATE / "documentation/preflight_gate_adjustment_v36.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "failure_count": report["failure_count"], "output": str(path)}, indent=2))
    if report["failure_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
