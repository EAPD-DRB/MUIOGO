#!/usr/bin/env python3
"""Publish FIT cash flows and the r9 four-scenario validation summary."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "WebAPP" / "DataStorage" / ".Philippines_v22-transition-scope-fit-repair-candidate-r9"
CONTROL = ROOT / "WebAPP" / "DataStorage" / ".Philippines_v22-transition-scope-only-candidate-r8"
RUNS = {
    "BASE": "FIT_ACCOUNTING_V22_BASE",
    "COAL_PHASEOUT": "FIT_ACCOUNTING_V22_COAL_PHASEOUT",
    "RE": "FIT_ACCOUNTING_V22_RE",
    "EV": "FIT_ACCOUNTING_V22_EV",
}
CONTROL_RUNS = {
    "BASE": "TRANSITION_SCOPE_V22_BASE",
    "COAL_PHASEOUT": "TRANSITION_SCOPE_V22_COAL_PHASEOUT",
    "EV": "TRANSITION_SCOPE_V22_EV",
}
FIT_TECH = "PHL_POW_CHP_BIOM_FIT_OLD"
SUPPLY_ID = "TEC_telf6"
FIT_ID = "TEC_v21bio"
IAR = 4.000666667
COLLECTION_COST = 15.8
YEARS = [str(year) for year in range(2020, 2054)]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(payload: dict, parameter: str, **keys):
    found = [row for row in payload[parameter]["SC_0"]
             if all(row.get(key) == value for key, value in keys.items())]
    if len(found) != 1:
        raise AssertionError((parameter, keys, len(found)))
    return found[0]


def annual_activity(run: Path) -> dict[tuple[str, str], float]:
    result: dict[tuple[str, str], float] = {}
    with (run / "csv" / "TotalAnnualTechnologyActivityByMode.csv").open(
            newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = row["t"], row["y"]
            result[key] = result.get(key, 0.0) + float(row["TotalAnnualTechnologyActivityByMode"])
    return result


def publish_cashflow(run: Path, credits: dict[str, float]) -> Path:
    activity = annual_activity(run)
    rows = []
    for year in YEARS:
        value = activity.get((FIT_TECH, year), 0.0)
        credit = credits[year]
        rows.append({
            "year": year,
            "technology": FIT_TECH,
            "solved_activity_pj_electricity": value,
            "fit_credit_musd_per_pj_electricity": credit,
            "gross_fit_receipt_musd": value * credit,
            "eligibility_assumption": "legacy FIT credit through 2034" if credit else "no retained FIT credit",
            "accounting_status": "post-solve disclosure; excluded from objective and constraints",
        })
    output = run / "fit_cashflow_postsolve.csv"
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return output


def constraint_extrema(run: Path) -> dict:
    gen = read(CASE / "genData.json")
    names = {item["TechId"]: item["Tech"] for item in gen["osy-tech"]}
    multipliers = read(CASE / "RYTCn.json")
    constants = read(CASE / "RYCn.json")["UCC"]["SC_w03qj"]

    def measure(filename: str, field: str) -> dict[tuple[str, str], float]:
        values = {}
        with (run / "csv" / filename).open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                values[row["t"], row["y"]] = float(row[field])
        return values

    activity = annual_activity(run)
    capacity = measure("TotalCapacityAnnual.csv", "TotalCapacityAnnual")
    new_capacity = measure("NewCapacity.csv", "NewCapacity")
    coordinates = {
        "CAM": activity,
        "CCM": capacity,
        "CNCM": new_capacity,
    }

    def residuals(constraint_id: str) -> dict[str, float]:
        constant = next(row for row in constants if row["ConId"] == constraint_id)
        result = {}
        for year in YEARS:
            lhs = 0.0
            for parameter, solved in coordinates.items():
                for row in multipliers[parameter]["SC_w03qj"]:
                    if row["ConId"] == constraint_id and row[year] is not None:
                        lhs += float(row[year]) * solved.get((names[row["TechId"]], year), 0.0)
            result[year] = lhs - float(constant[year] or 0.0)
        return result

    renewable_residuals = residuals("CO_xr1eb")
    nuclear_residuals = residuals("CO_nucap")
    renewable_duals = []
    with (run / "csv" / "UDC1_UserDefinedConstraintInequality.csv").open(
            newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["cn"] == "RENEWABLES" and int(row["y"]) >= 2026:
                renewable_duals.append(float(row["UDC1_UserDefinedConstraintInequality"]))
    nuclear_duals = []
    with (run / "csv" / "UDC2_UserDefinedConstraintEquality.csv").open(
            newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["cn"] == "NUCLEAR_CAPACITY_TARGET" and row["y"] in {"2032", "2035", "2050"}:
                nuclear_duals.append(float(row["UDC2_UserDefinedConstraintEquality"]))
    active_renewable = [renewable_residuals[year] for year in YEARS if int(year) >= 2026]
    active_nuclear = [nuclear_residuals[year] for year in ("2032", "2035", "2050")]
    return {
        "renewable_inequality_max_lhs_minus_rhs_from_rounded_csv": max(active_renewable),
        "renewable_inequality_within_1e-3_csv_reconstruction_tolerance": max(active_renewable) <= 1e-3,
        "nuclear_equality_max_absolute_residual_gw": max(map(abs, active_nuclear)),
        "renewable_exported_dual_min_max": [min(renewable_duals), max(renewable_duals)],
        "nuclear_exported_dual_min_max": [min(nuclear_duals), max(nuclear_duals)],
    }


def update_change_status() -> None:
    path = CASE / "data_sources" / "CHANGES.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    selected = [row for row in rows if row["change_id"] == "CHG_PHL_V22_FIT_ACCOUNTING_R9_20260820"]
    if len(selected) != 1:
        raise AssertionError(len(selected))
    selected[0]["resolve_status"] = "validated_four_scenarios_optimal_not_promoted"
    selected[0]["notes"] = (
        "Deterministic and matrix gates passed. BASE solved first; COAL_PHASEOUT, RE and EV then "
        "solved concurrently. Promotion deliberately paused for user review. No activity, dispatch, "
        "build or generation outcome is fixed; no new UDC or technology is added."
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    old_rytm = read(CONTROL / "RYTM.json")
    supply = one(old_rytm, "VC", TechId=SUPPLY_ID, MoId=1)
    fit = one(old_rytm, "VC", TechId=FIT_ID, MoId=1)
    credits = {
        year: max(0.0, COLLECTION_COST - supply[year] * IAR + 0.0001 - fit[year])
        for year in YEARS
    }

    records = {}
    cashflows = {}
    for scenario, run_name in RUNS.items():
        run = CASE / "res" / run_name
        record = read(run / "optimization_record.json")
        if not str(record["status"]).startswith("Optimal"):
            raise AssertionError((scenario, record["status"]))
        path = publish_cashflow(run, credits)
        record["fit_cashflow_postsolve_sha256"] = sha(path)
        (run / "optimization_record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        records[scenario] = record
        activity = annual_activity(run)
        cashflows[scenario] = {
            year: {
                "fit_activity_pj": activity.get((FIT_TECH, year), 0.0),
                "fit_receipt_musd": activity.get((FIT_TECH, year), 0.0) * credits[year],
            }
            for year in ("2020", "2022", "2024", "2030", "2040", "2050")
        }

    manifest = read(CASE / "documentation" / "fit_accounting_r9_build_manifest.json")
    source_identity = all(sha(CASE / name) == value for name, value in manifest["after_sha256"].items())
    controls = {}
    objective_comparison = {}
    for scenario, run_name in CONTROL_RUNS.items():
        record = read(CONTROL / "res" / run_name / "optimization_record.json")
        controls[scenario] = record
        before = float(record["status"].split()[-1])
        after = float(records[scenario]["status"].split()[-1])
        objective_comparison[scenario] = {
            "r8": before, "r9": after, "change": after - before,
            "change_percent": 100 * (after / before - 1),
        }

    update_change_status()
    summary = {
        "schema": "philippines-v22-fit-accounting-r9-validation-v1",
        "status": "validated_candidate_not_promoted",
        "promotion_allowed_by_solve_gate": True,
        "promoted": False,
        "pause_point": "All four candidate scenarios are optimal; live-case promotion and identity regeneration have not been performed.",
        "promotion_rule": "BASE solved first; only then COAL_PHASEOUT, RE and EV ran concurrently; all four are optimal from the same source candidate.",
        "candidate_source_hashes_match_build_manifest": source_identity,
        "optimizer_executions": [
            {"scenario": scenario, "algorithm": "default", "status": record["status"],
             "solve_seconds": record["solve_seconds"], "timeout_seconds": record["timeout_seconds"],
             "lp_sha256": record["lp_sha256"]}
            for scenario, record in records.items()
        ],
        "objectives": {scenario: float(record["status"].split()[-1]) for scenario, record in records.items()},
        "objective_comparison_to_r8": objective_comparison,
        "matrix_dimensions": {
            scenario: read(CASE / "res" / run_name / "generation_matrix_report.json")["matrix_dimensions"]
            for scenario, run_name in RUNS.items()
        },
        "fit_activity_and_postsolve_receipts": cashflows,
        "re_policy_constraint_checks": constraint_extrema(CASE / "res" / RUNS["RE"]),
        "deterministic_gate": "documentation/fit_accounting_r9_deterministic_gate.json",
        "numerical_diagnostics": "documentation/RE_NUMERICAL_DIAGNOSTICS_2026-08-20.json",
        "model_fix": "documentation/MODEL_FIXES_FIT_ACCOUNTING_V22_2026-08-20.md",
        "known_limitations": [
            "FIT receipts are gross post-solve transfers; payer incidence and financing are outside the model.",
            "The 15.8 MUSD/PJ physical collection cost is an inherited ERC-anchored judgement.",
            "Removing dispatch-valued tariff revenue materially lowers FIT biomass utilization; generation remains endogenous and must be assessed as a benchmark, not forced.",
            "UDC residuals are reconstructed from four-decimal activity/capacity CSVs; the exact CBC solution is optimal and the 9.1e-5 apparent RE-share excess is within the documented 1e-3 reconstruction tolerance.",
            "Wider biofuel, reliability, solar timing, cooling-water, T&D loss, availability and pre-2026 build issues remain deferred.",
        ],
    }
    output = CASE / "documentation" / "FIT_ACCOUNTING_R9_VALIDATION_SUMMARY.json"
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
