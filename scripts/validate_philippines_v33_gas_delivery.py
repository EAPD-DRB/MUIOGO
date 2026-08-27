#!/usr/bin/env python3
"""Deterministic pre-solve gate for the Philippines v33 gas-cost candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


YEARS = [str(year) for year in range(2020, 2054)]
OLD_GAS = "PHL_POW_CHP_NG_OLD"
REFERENCE_GAS = "PHL_POW_PP_NGCC"
END_USE_TECHS = (
    "PHL_AGR_HEAT_NG",
    "PHL_INDU_OTHHPH_NG",
    "PHL_INDU_OTHHPH_NG_CCS",
    "PHL_INDU_OTHLPH_NG",
    "PHL_POW_BH2_NG",
    "PHL_POW_GH2_NG",
    "PHL_SER_HEAT_NG",
    "PHL_TRA_23WHEEL_NG",
    "PHL_TRA_BUS_NG", "PHL_TRA_CAR_NG", "PHL_TRA_TRUH_NG",
    "PHL_TRA_TRUL_NG", "PHL_TRA_VAN_NG", "PHL_HOU_COOK_NG",
)
DELIVERY_ADDER = 8.2
EXPECTED_VOM = 0.7050283513976835
EPSILON_VC = 0.0001
EVIDENCE_SHA256 = "5a9de93aa4ae8c3768de6decf8a4b9e274c207d12c9a925e96bf63712cb6bc4e"
POWER_GAS_TECHS = {OLD_GAS, REFERENCE_GAS, "PHL_POW_PP_NGCC_CCS"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def one(rows: list[dict], **coordinates: object) -> dict:
    matches = [row for row in rows if all(row.get(key) == value for key, value in coordinates.items())]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one row at {coordinates}, found {len(matches)}")
    return matches[0]


def csv_id_count(path: Path, field: str, identifier: str) -> int:
    with path.open(newline="") as stream:
        return sum(row[field] == identifier for row in csv.DictReader(stream))


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    baseline = args.baseline.resolve()
    candidate = args.candidate.resolve()
    checks: dict[str, object] = {}

    base_gen = json.loads((baseline / "genData.json").read_text())
    cand_gen = json.loads((candidate / "genData.json").read_text())
    identity_differences = {
        key: [base_gen.get(key), cand_gen.get(key)]
        for key in sorted(set(base_gen) | set(cand_gen))
        if base_gen.get(key) != cand_gen.get(key)
    }
    checks["genData_only_identity_changed"] = (
        {"osy-casename", "osy-desc"} <= set(identity_differences)
        and set(identity_differences) <= {"osy-casename", "osy-desc", "osy-date"}
    )
    checks["candidate_identity_is_v33"] = cand_gen.get("osy-casename") == "Philippines_v33"
    tech_ids = {row["Tech"]: row["TechId"] for row in cand_gen["osy-tech"]}
    comm_ids = {row["Comm"]: row["CommId"] for row in cand_gen["osy-comm"]}

    base_vc = json.loads((baseline / "RYTM.json").read_text())
    cand_vc = json.loads((candidate / "RYTM.json").read_text())
    base_iar = json.loads((baseline / "RYTCM.json").read_text())
    base_rows = base_vc["VC"]["SC_0"]
    cand_rows = cand_vc["VC"]["SC_0"]
    iar_rows = base_iar["IAR"]["SC_0"]
    checks["vc_row_count_unchanged"] = len(base_rows) == len(cand_rows)

    gas_id = comm_ids["PHL_PRO_NG"]
    electricity_id = comm_ids["PHL_POW_ELE"]
    allowed_ids = {tech_ids[name] for name in (OLD_GAS, *END_USE_TECHS)}
    changed_cells: list[dict[str, object]] = []
    forbidden_changes: list[dict[str, object]] = []
    for row_index, (before, after) in enumerate(zip(base_rows, cand_rows)):
        for field in sorted(set(before) | set(after)):
            if before.get(field) == after.get(field):
                continue
            item = {"row": row_index, "field": field, "before": before.get(field), "after": after.get(field)}
            allowed = field in YEARS and before.get("TechId") in allowed_ids and before.get("MoId") == 1
            (changed_cells if allowed else forbidden_changes).append(item)
    checks["exactly_510_allowed_vc_cells_changed"] = len(changed_cells) == 510
    checks["no_forbidden_rytm_changes"] = not forbidden_changes

    formula_checks: list[bool] = []
    old_before = one(base_rows, TechId=tech_ids[OLD_GAS], MoId=1)
    old_after = one(cand_rows, TechId=tech_ids[OLD_GAS], MoId=1)
    ref = one(base_rows, TechId=tech_ids[REFERENCE_GAS], MoId=1)
    for year in YEARS:
        formula_checks.append(float(ref[year]) == EXPECTED_VOM)
        expected = (
            float(old_before[year]) + EXPECTED_VOM - EPSILON_VC
            if year in {"2020", "2021"} else EXPECTED_VOM
        )
        formula_checks.append(float(old_after[year]) == expected)
    checks["old_gas_vom_exact_and_take_or_pay_retained"] = all(formula_checks)

    end_use_checks: list[bool] = []
    for technology in END_USE_TECHS:
        before = one(base_rows, TechId=tech_ids[technology], MoId=1)
        after = one(cand_rows, TechId=tech_ids[technology], MoId=1)
        iar = one(iar_rows, TechId=tech_ids[technology], CommId=gas_id, MoId=1)
        for year in YEARS:
            expected = float(before[year]) + float(iar[year]) * DELIVERY_ADDER
            end_use_checks.append(float(after[year]) == expected)
    checks["all_476_nonpower_delivery_cells_follow_exact_formula"] = len(end_use_checks) == 476 and all(end_use_checks)

    gas_consumer_ids = {
        row["TechId"] for row in iar_rows
        if row.get("CommId") == gas_id and any(float(row[year]) != 0 for year in YEARS)
    }
    expected_gas_consumer_ids = {
        tech_ids[name] for name in (*END_USE_TECHS, *POWER_GAS_TECHS)
    }
    oar_rows = base_iar["OAR"]["SC_0"]
    output_class_checks = []
    for technology in END_USE_TECHS:
        output_class_checks.append(not any(
            row.get("TechId") == tech_ids[technology]
            and row.get("CommId") == electricity_id
            and any(float(row[year]) != 0 for year in YEARS)
            for row in oar_rows
        ))
    for technology in POWER_GAS_TECHS:
        output_class_checks.append(any(
            row.get("TechId") == tech_ids[technology]
            and row.get("CommId") == electricity_id
            and any(float(row[year]) != 0 for year in YEARS)
            for row in oar_rows
        ))
    checks["processed_gas_consumer_partition_complete"] = (
        gas_consumer_ids == expected_gas_consumer_ids and all(output_class_checks)
    )

    policy_checks: list[bool] = []
    for scenario in sorted(set(cand_vc["VC"]) - {"SC_0"}):
        for technology in (OLD_GAS, *END_USE_TECHS):
            row = one(cand_vc["VC"][scenario], TechId=tech_ids[technology], MoId=1)
            policy_checks.extend(row[year] is None for year in YEARS)
    checks["no_policy_scenario_vc_overrides"] = bool(policy_checks) and all(policy_checks)

    unchanged = {}
    for path in sorted(baseline.glob("RY*.json")):
        if path.name == "RYTM.json":
            continue
        unchanged[path.name] = sha256(path) == sha256(candidate / path.name)
    checks["all_other_parameter_json_unchanged"] = all(unchanged.values())
    checks["demand_stock_efficiency_and_bounds_unchanged"] = all(
        unchanged.get(name, False) for name in ("RYC.json", "RYT.json", "RYTCM.json", "RYTs.json")
    )
    checks["no_activity_or_share_bound_change"] = all(
        unchanged.get(name, False) for name in ("RYT.json", "RYTs.json")
    )

    evidence = candidate / "data_sources/evidence/v33_gas_delivery/elizabethtown_cng_vs_traditional_fuels.html"
    checks["archived_evidence_hash_exact"] = evidence.is_file() and sha256(evidence) == EVIDENCE_SHA256
    ledgers = candidate / "data_sources"
    ledger_ids = {
        "source": csv_id_count(ledgers / "SOURCES.csv", "source_id", "SRC_PHL_V33_ETOWN_CNG_DELIVERY"),
        "source_doe": csv_id_count(ledgers / "SOURCES.csv", "source_id", "SRC_PHL_V33_DOE_ENERGY_INVESTMENT_2024"),
        "assumption_midpoint": csv_id_count(ledgers / "ASSUMPTIONS.csv", "assumption_id", "ASM_PHL_V33_GAS_DELIVERY_MIDPOINT"),
        "assumption_proxy": csv_id_count(ledgers / "ASSUMPTIONS.csv", "assumption_id", "ASM_PHL_V33_NONPOWER_DELIVERY_PROXY"),
        "assumption_contract": csv_id_count(ledgers / "ASSUMPTIONS.csv", "assumption_id", "ASM_PHL_V33_RETAIN_TAKE_OR_PAY"),
        "calculation_delivery": csv_id_count(ledgers / "CALCULATIONS.csv", "calculation_id", "CALC_PHL_V33_GAS_DELIVERY_ADDER"),
        "calculation_vom": csv_id_count(ledgers / "CALCULATIONS.csv", "calculation_id", "CALC_PHL_V33_OLD_GAS_VOM"),
        "change": csv_id_count(ledgers / "CHANGES.csv", "change_id", "CHG_PHL_V33_GAS_DELIVERY"),
    }
    ledger_ids["maps"] = sum(
        csv_id_count(ledgers / "MODEL_MAP.csv", "map_id", f"MAP_PHL_V33_GAS_VC_{index:02d}")
        for index in range(1, 16)
    )
    ledger_ids["gap"] = csv_id_count(
        ledgers / "GAPS.csv", "item", "Philippines-specific gas distribution and CNG station cost evidence"
    )
    checks["provenance_rows_present_once"] = all(
        value == (15 if key == "maps" else 1) for key, value in ledger_ids.items()
    )

    run_directories = sorted(path.name for path in (candidate / "res").iterdir() if path.is_dir())
    checks["clean_zero_run_inventory"] = not run_directories
    audit = json.loads((candidate / "documentation/gas_delivery_source_change_v33.json").read_text())
    checks["source_audit_matches_candidate"] = (
        audit.get("changed_cells") == 510
        and audit.get("non_forcing") is True
        and audit.get("take_or_pay_retained") is True
        and audit.get("candidate_source_hashes", {}).get("RYTM.json") == sha256(candidate / "RYTM.json")
    )

    scalar_checks = [value for value in checks.values() if isinstance(value, bool)]
    status = "pass" if all(scalar_checks) else "fail"
    report = {
        "case": "Philippines_v33", "parent_case": "Philippines_v32",
        "gate": "gas_delivery_deterministic_pre_solve", "status": status,
        "optimizer_runs": 0, "model_generation_runs": 0,
        "canonical_baseline": {
            "case": "Philippines_v32", "run": "BASE_V32_RICE_YIELD",
            "objective": 838560.95562083, "runtime_seconds": 66.15766029099905,
            "matrix": {"rows": 467075, "columns": 517844, "matrix_nonzeros": 8194641},
        },
        "classification": {
            "observed_gas_generation": "benchmark-only validation value",
            "doe_gross_generation": "benchmark-only validation value",
            "electricity_sector_demands": "inherited exogenous final demands; unchanged in this candidate",
            "take_or_pay": "inherited economic contract term; retained by explicit direction",
            "legacy_gas_power": "physical conversion stock",
            "road_cng_and_gas_cooking": "physical end-use conversions",
        },
        "equation_mapping": {
            "source": "RYTM.json / VC / SC_0",
            "generated": "VariableCost",
            "formulation": "OC1_OperatingCostsVariable and total discounted cost in SOLVERs/model.v.5.4.txt",
            "effect": "Changes endogenous order of merit only; no activity equation or envelope is altered.",
        },
        "deterministic_envelope_proof": {
            "method": "Byte identity of every RY*.json physical/demand parameter file except RYTM.json",
            "unchanged_files": unchanged,
            "conclusion": "Initial capacity, survival, replacement, demand and commodity-conversion envelopes are exactly v32.",
        },
        "checks": checks, "identity_differences": identity_differences,
        "changed_cells": len(changed_cells), "forbidden_changes": forbidden_changes,
        "ledger_id_counts": ledger_ids, "run_directories": run_directories,
    }
    output = candidate / "documentation/preflight_gas_delivery_v33.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
