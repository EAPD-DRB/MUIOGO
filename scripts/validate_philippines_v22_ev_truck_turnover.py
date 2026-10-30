#!/usr/bin/env python3
"""Deterministic source validation for the v22 EV/truck-turnover correction."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from apply_philippines_v22_ev_truck_turnover import (
    YEARS, SPEC_PATH, build_truck_envelopes, constraint_rows, read, rows_by_id,
)
from validate_osemosys_physical_gate import validate_case as physical_gate


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(candidate: Path, baseline: Path) -> dict:
    spec = read(SPEC_PATH)
    gen = read(candidate / "genData.json")
    baseline_gen = read(baseline / "genData.json")
    assert gen == baseline_gen
    scenarios = {row["Scenario"]: row["ScenarioId"] for row in gen["osy-scenarios"]}
    base, ev = scenarios["BASE"], scenarios["EV"]
    constraint = next(row for row in gen["osy-constraints"] if row["ConId"] == spec["constraint_id"])
    ev_technologies = tuple(constraint["CM"])
    ryt, old_ryt = read(candidate / "RYT.json"), read(baseline / "RYT.json")
    rytcn, old_rytcn = read(candidate / "RYTCn.json"), read(baseline / "RYTCn.json")
    base_tamaxci = rows_by_id(ryt, "TAMaxCI", base, "TechId")
    ev_tamaxci = rows_by_id(ryt, "TAMaxCI", ev, "TechId")
    old_base_tamaxci = rows_by_id(old_ryt, "TAMaxCI", base, "TechId")
    residual = rows_by_id(ryt, "RC", base, "TechId")
    envelopes = build_truck_envelopes(candidate, spec)
    checks = []

    def check(name: str, passed: bool, detail=None):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("eleven_constraint_members", len(ev_technologies) == 11)
    check("constraint_tag_unchanged_equality", constraint["Tag"] == 1)
    check("all_ev_residual_capacity_zero", all(
        abs(float(residual[t][y])) <= 1e-12 for t in ev_technologies for y in YEARS))
    check("base_ev_investment_zero_full_horizon", all(
        float(base_tamaxci[t][y]) == 0.0 for t in ev_technologies for y in YEARS))
    check("ev_scenario_truck_envelopes_explicit", all(
        ev_tamaxci[t][y] == envelopes[t][y] for t in envelopes if t in ev_technologies for y in YEARS))
    check("ev_scenario_other_ev_envelopes_restored", all(
        ev_tamaxci[t][y] == old_base_tamaxci[t][y]
        for t in ev_technologies if t not in envelopes for y in YEARS))
    check("base_non_ev_truck_envelopes_repaired", all(
        base_tamaxci[t][y] == values[y]
        for t, values in envelopes.items() if t not in ev_technologies for y in YEARS))
    for policy in (scenarios["COAL_PHASEOUT"], scenarios["RE"]):
        policy_rows = rows_by_id(ryt, "TAMaxCI", policy, "TechId")
        check(f"{policy}_inherits_base_ev_ban", all(
            policy_rows[t][y] is None for t in ev_technologies for y in YEARS))

    base_cam = constraint_rows(rytcn, "CAM", base, spec["constraint_id"])
    ev_cam = constraint_rows(rytcn, "CAM", ev, spec["constraint_id"])
    old_base_cam = constraint_rows(old_rytcn, "CAM", base, spec["constraint_id"])
    check("base_udc_cam_deactivated", all(base_cam[t][y] == 0 for t in ev_technologies for y in YEARS))
    check("ev_udc_cam_explicitly_restored", all(
        ev_cam[t][y] == old_base_cam[t][y] for t in ev_technologies for y in YEARS))
    check("constraint_rhs_unchanged", digest(candidate / "RYCn.json") == digest(baseline / "RYCn.json"))
    for parameter in ("CNCM", "CCM"):
        check(f"{parameter}_unchanged", rytcn[parameter] == old_rytcn[parameter])

    source_names = sorted(path.name for path in baseline.glob("*.json"))
    changed = [name for name in source_names if digest(candidate / name) != digest(baseline / name)]
    check("only_intended_source_files_changed", changed == ["RYT.json", "RYTCn.json"], changed)

    gates = {}
    for scenario_name, scenario_id in scenarios.items():
        gate = physical_gate(candidate, scenario=scenario_id, historical_through=2020)
        gates[scenario_name] = {
            "status": gate["status"], "failure_count": gate["failure_count"],
            "failures": gate["failures"][:20],
        }
        check(f"generic_physical_gate_{scenario_name}", gate["status"] != "failed", gates[scenario_name])

    failed = [row for row in checks if not row["passed"]]
    report = {
        "schema": "philippines-v22-ev-truck-turnover-deterministic-validation-v1",
        "candidate": str(candidate), "baseline": str(baseline),
        "status": "passed" if not failed else "failed",
        "checks": checks, "failed_checks": failed,
        "generic_physical_gates": gates, "optimizer_runs": 0,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.candidate.resolve(), args.baseline.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
