#!/usr/bin/env python3
"""Finalize candidate validation evidence and its six-file schema ledger."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


SCENARIOS = ("BASE", "COAL_PHASEOUT", "RE", "EV")
RUNS = {scenario: f"EV_TRUCK_TURNOVER_V22_{scenario}" for scenario in SCENARIOS}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def append_unique(path: Path, key: str, row: dict[str, object]) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    assert fieldnames is not None
    if any(existing[key] == str(row[key]) for existing in rows):
        return
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writerow({name: row.get(name, "") for name in fieldnames})


def update_change(path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    assert fieldnames is not None
    matches = [row for row in rows if row["change_id"] == "CHG_PHL_V22_EV_TRUCK_TURNOVER_20260824"]
    if len(matches) != 1:
        raise RuntimeError("expected exactly one EV/truck change-ledger row")
    matches[0]["resolve_status"] = "validated_candidate_four_scenario_optimal_pending_promotion"
    matches[0]["notes"] = (
        "No activity/share/diesel target was added. The generic AAD-aware physical gate, "
        "source checks and four GLPK matrix checks passed. BASE solved optimally first; "
        "COAL_PHASEOUT, RE and EV then solved concurrently and all were optimal. "
        "Candidate validation manifest retains hashes, runtimes, objectives and comparisons."
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    documentation = candidate / "documentation"
    snapshots = candidate / "data_sources/snapshots"

    deterministic_path = documentation / "ev_truck_turnover_deterministic_validation.json"
    comparison_path = documentation / "ev_truck_turnover_result_comparison.json"
    rejected_path = documentation / "ev_truck_turnover_rejected_r2_physical_gate.json"
    canonical_path = documentation / "ev_truck_turnover_canonical_r9_physical_gate.json"
    deterministic = json.loads(deterministic_path.read_text())
    comparison = json.loads(comparison_path.read_text())
    rejected = json.loads(rejected_path.read_text())
    canonical = json.loads(canonical_path.read_text())

    if deterministic["status"] != "passed" or deterministic["failed_checks"]:
        raise RuntimeError("deterministic validation did not pass")
    if rejected["failure_count"] != 6 or canonical["failure_count"] != 0:
        raise RuntimeError("generic-gate regression controls do not match the expected 6/0 result")

    scenario_records = {}
    for scenario, run in RUNS.items():
        run_dir = candidate / "res" / run
        matrix = json.loads((run_dir / "generation_matrix_report.json").read_text())
        optimization = json.loads((run_dir / "optimization_record.json").read_text())
        result = comparison["scenarios"][scenario]
        if matrix["status"] != "passed" or not optimization["status"].startswith("Optimal"):
            raise RuntimeError(f"{scenario} did not pass matrix and optimization validation")
        if scenario != "EV":
            if result["candidate_ev_max_activity"] != 0 or result["candidate_ev_max_capacity"] != 0:
                raise RuntimeError(f"{scenario} violates the zero-EV counterfactual")
        elif result["candidate_active_ev_target_max_abs_residual"] > 0.00011:
            raise RuntimeError("EV equality differs from its retained target beyond CSV precision")
        scenario_records[scenario] = {
            "run": run,
            "active_scenarios": matrix["active_scenarios"],
            "matrix_status": matrix["status"],
            "matrix_dimensions": matrix["matrix_dimensions"],
            "data_sha256": matrix["hashes"]["data.txt"],
            "processed_data_sha256": matrix["hashes"]["data_processed.txt"],
            "lp_sha256": matrix["hashes"]["lp.lp"],
            "solver_status": optimization["status"],
            "solve_seconds": optimization["solve_seconds"],
            "results_sha256": optimization["results_sha256"],
            "objective_comparison": result["objective"],
            "ev_max_activity": result["candidate_ev_max_activity"],
            "ev_max_capacity": result["candidate_ev_max_capacity"],
            "active_ev_target_max_abs_residual": result["candidate_active_ev_target_max_abs_residual"],
        }

    manifest = {
        "schema": "philippines-v22-ev-truck-turnover-validation-v1",
        "date": "2026-08-24",
        "status": "validated_candidate_four_scenario_optimal_pending_promotion",
        "optimizer_run_count": 4,
        "optimizer_sequence": [
            "BASE completed proven optimal",
            "COAL_PHASEOUT, RE and EV launched concurrently after BASE passed",
        ],
        "generic_gate": {
            "unit_tests": "2 passed",
            "rejected_r2": {"status": rejected["status"], "failure_count": rejected["failure_count"]},
            "canonical_r9": {"status": canonical["status"], "failure_count": canonical["failure_count"]},
            "candidate_scenarios": deterministic["generic_physical_gates"],
        },
        "source_validation": {
            "status": deterministic["status"],
            "changed_root_source_files": ["RYT.json", "RYTCn.json"],
            "constraint_tag": "unchanged equality",
            "constraint_rhs": "unchanged",
            "residual_capacity": "zero for all 11 EV/PHEV technologies",
        },
        "scenario_records": scenario_records,
        "comparison_report_sha256": sha256(comparison_path),
        "deterministic_report_sha256": sha256(deterministic_path),
        "rejected_gate_report_sha256": sha256(rejected_path),
        "canonical_gate_report_sha256": sha256(canonical_path),
    }
    manifest_path = snapshots / "ev_truck_turnover_validation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest_hash = sha256(manifest_path)

    append_unique(candidate / "data_sources/SOURCES.csv", "source_id", {
        "source_id": "SRC_PHL_V22_EV_TRUCK_VALIDATION",
        "provider": "MUIOGO",
        "product": "Philippines v22 EV/truck four-scenario validation manifest",
        "edition": "2026-08-24",
        "reference_period": "2020-2053",
        "geography": "Philippines",
        "variable": "generic physical-gate, matrix, solver, EV availability and objective comparison results",
        "source_unit": "status; SHA-256; seconds; model objective units",
        "exact_locator": "data_sources/snapshots/ev_truck_turnover_validation_manifest.json",
        "access_date": "2026-08-24",
        "license": "Repository license",
        "sha256": manifest_hash,
        "local_file": "snapshots/ev_truck_turnover_validation_manifest.json",
        "notes": "BASE solved first; the three policy scenarios solved concurrently only after BASE was proven optimal.",
    })
    append_unique(candidate / "data_sources/CALCULATIONS.csv", "calculation_id", {
        "calculation_id": "CALC_PHL_V22_EV_TRUCK_VALIDATION",
        "formula": "generic AAD-aware physical gate + source assertions + GLPK matrix check + CBC optimum + canonical r9 result comparison",
        "source_ids": "SRC_PHL_V22_EV_TRUCK_FORMULATION;SRC_PHL_V22_EV_TRUCK_VALIDATION",
        "assumption_ids": "ASM_PHL_V22_BASE_ZERO_EV;ASM_PHL_V22_TRUCK_REPLACEMENT_ENVELOPE",
        "input_values": "rejected r2; canonical r9; BASE; COAL_PHASEOUT; RE; EV",
        "input_units": "cases;scenarios",
        "output_value": "6 rejected-r2 shortfalls; 0 canonical/candidate gate failures; 4 optimal candidate scenarios",
        "output_unit": "count;status",
        "script_path": "scripts/validate_osemosys_physical_gate.py;scripts/validate_philippines_v22_ev_truck_turnover.py;scripts/compare_philippines_v22_ev_truck_turnover.py",
        "script_version": "v1",
        "notes": "The EV equality target is unchanged; its maximum active-year residual is within 0.0001 CSV output precision.",
    })
    append_unique(candidate / "data_sources/MODEL_MAP.csv", "map_id", {
        "map_id": "MAP_PHL_V22_EV_TRUCK_VALIDATION",
        "model_file": "res/EV_TRUCK_TURNOVER_V22_*/;data_sources/snapshots/ev_truck_turnover_validation_manifest.json",
        "parameter": "TAMaxCI;CAM;UCC;NewCapacity;TotalCapacityAnnual;TotalAnnualTechnologyActivityByMode;ObjectiveValue",
        "entity": "CO_sdx29;11 EV/PHEV technologies;TURN_TRUL;TURN_TRUH",
        "scenario": "BASE;COAL_PHASEOUT;RE;EV",
        "years": "2020-2053",
        "value_or_expression": "all four optimal; zero EV capacity/activity in BASE/COAL_PHASEOUT/RE; existing EV equality retained",
        "model_unit": "status;10^3 vehicles;activity;objective",
        "evidence_ids": "SRC_PHL_V22_EV_TRUCK_VALIDATION;CALC_PHL_V22_EV_TRUCK_VALIDATION",
        "evidence_type": "candidate validation",
        "notes": "Run-specific artifacts are authoritative; no shared viewer output was generated concurrently.",
    })
    update_change(candidate / "data_sources/CHANGES.csv")
    print(json.dumps({"status": manifest["status"], "manifest": str(manifest_path), "sha256": manifest_hash}, indent=2))


if __name__ == "__main__":
    main()
