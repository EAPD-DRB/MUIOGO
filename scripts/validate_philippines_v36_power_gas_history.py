#!/usr/bin/env python3
"""Deterministic equation-first gate for the Philippines v36 power/gas candidate."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from pathlib import Path

import build_philippines_v36_power_gas_history as build


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "WebAPP/DataStorage/Philippines_v33"
CANDIDATE = ROOT / "WebAPP/DataStorage/.Philippines_v36-power-gas-history-candidate-20260827"
OUTPUT = CANDIDATE / "documentation/preflight_power_gas_history_v36.json"
YEARS = build.YEARS
OBSERVED_GAS_PJ = {"2022": 64.3824, "2023": 60.0048, "2024": 64.9692}
CAPACITY_TO_ACTIVITY = 31.536
TOL = 1e-10


def load(case: Path, name: str) -> dict:
    return json.loads((case / name).read_text(encoding="utf-8"))


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


def replace_row(target: list[dict], source: list[dict], **coordinates: object) -> None:
    target_row = one(target, **coordinates)
    source_row = one(source, **coordinates)
    target[target.index(target_row)] = copy.deepcopy(source_row)


def close(left: float, right: float, tol: float = TOL) -> bool:
    return abs(float(left) - float(right)) <= tol * max(1.0, abs(float(right)))


def csv_ids(path: Path, field: str) -> list[str]:
    with path.open(newline="", encoding="utf-8") as stream:
        return [row[field] for row in csv.DictReader(stream)]


def main() -> None:
    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: object) -> None:
        checks.append({"name": name, "status": "pass" if passed else "fail", "detail": detail})

    base_gen = load(BASELINE, "genData.json")
    cand_gen = load(CANDIDATE, "genData.json")
    base_ids = {
        "tech": {row["Tech"]: row["TechId"] for row in base_gen["osy-tech"]},
        "comm": {row["Comm"]: row["CommId"] for row in base_gen["osy-comm"]},
    }
    cand_ids = {
        "tech": {row["Tech"]: row["TechId"] for row in cand_gen["osy-tech"]},
        "comm": {row["Comm"]: row["CommId"] for row in cand_gen["osy-comm"]},
    }
    old_gas_id = cand_ids["tech"][build.OLD_GAS]
    td_id = cand_ids["tech"][build.TD]
    gross_id = cand_ids["comm"][build.GROSS_ELECTRICITY]
    gas_id = cand_ids["comm"]["PHL_PRO_NG"]
    extraction_id = cand_ids["tech"]["PHL_PRO_EXTR_NG"]
    import_id = cand_ids["tech"]["PHL_PRO_IMP_NG"]

    check("identity_sets_unchanged", base_ids == cand_ids, {"case": cand_gen.get("osy-casename")})
    normalized_gen = copy.deepcopy(cand_gen)
    for key in ("osy-casename", "osy-date", "osy-desc"):
        normalized_gen[key] = base_gen[key]
    one(normalized_gen["osy-tech"], Tech=build.OLD_GAS)["Desc"] = one(
        base_gen["osy-tech"], Tech=build.OLD_GAS
    )["Desc"]
    check("gen_data_diff_scope", normalized_gen == base_gen, "identity, case description and legacy-gas description only")

    unchanged_root = [
        "R.json", "RE.json", "RS.json", "RT.json", "RTSM.json", "RYS.json",
        "RYC.json", "RYCn.json", "RYCTs.json", "RYDtb.json", "RYE.json",
        "RYSeDt.json", "RYS.json", "RYT.json", "RYTC.json", "RYTCM.json",
        "RYTCn.json", "RYTEM.json", "RYTM.json", "RYTs.json", "RYTTs.json",
    ]
    allowed_changed = {"RYT.json", "RYTM.json", "RYTCM.json", "RYTEM.json"}
    unchanged_hashes = {
        name: sha256(BASELINE / name) == sha256(CANDIDATE / name)
        for name in unchanged_root if name not in allowed_changed
    }
    check("unaffected_source_files_exact", all(unchanged_hashes.values()), unchanged_hashes)
    check(
        "final_demand_exactly_unchanged",
        sha256(BASELINE / "RYC.json") == sha256(CANDIDATE / "RYC.json"),
        "No residual electricity-demand fit was introduced.",
    )

    base_ryt, cand_ryt = load(BASELINE, "RYT.json"), load(CANDIDATE, "RYT.json")
    normalized = copy.deepcopy(cand_ryt)
    for parameter in ("RC", "AF", "FC"):
        replace_row(normalized[parameter]["SC_0"], base_ryt[parameter]["SC_0"], TechId=old_gas_id)
    check("ryt_diff_scope", normalized == base_ryt, "SC_0 legacy-gas RC, AF and FC only")

    base_rytm, cand_rytm = load(BASELINE, "RYTM.json"), load(CANDIDATE, "RYTM.json")
    normalized = copy.deepcopy(cand_rytm)
    for parameter in ("VC", "TAMUL"):
        for mode in (1, 2):
            replace_row(
                normalized[parameter]["SC_0"], base_rytm[parameter]["SC_0"],
                TechId=old_gas_id, MoId=mode,
            )
    check("rytm_diff_scope", normalized == base_rytm, "SC_0 legacy-gas VC and TAMUL modes 1-2 only")

    base_rytcm, cand_rytcm = load(BASELINE, "RYTCM.json"), load(CANDIDATE, "RYTCM.json")
    normalized = copy.deepcopy(cand_rytcm)
    replace_row(
        normalized["IAR"]["SC_0"], base_rytcm["IAR"]["SC_0"],
        TechId=td_id, CommId=gross_id, MoId=1,
    )
    for parameter in ("IAR", "OAR"):
        for source_row in base_rytcm[parameter]["SC_0"]:
            if source_row.get("TechId") != old_gas_id or source_row.get("MoId") not in (1, 2):
                continue
            replace_row(
                normalized[parameter]["SC_0"], base_rytcm[parameter]["SC_0"],
                TechId=old_gas_id, CommId=source_row["CommId"], MoId=source_row["MoId"],
            )
    check("rytcm_diff_scope", normalized == base_rytcm, "TD IAR and legacy-gas physical modes only")

    base_rytem, cand_rytem = load(BASELINE, "RYTEM.json"), load(CANDIDATE, "RYTEM.json")
    normalized = copy.deepcopy(cand_rytem)
    for source_row in base_rytem["EAR"]["SC_0"]:
        if source_row.get("TechId") != old_gas_id or source_row.get("MoId") not in (1, 2):
            continue
        replace_row(
            normalized["EAR"]["SC_0"], base_rytem["EAR"]["SC_0"],
            TechId=old_gas_id, EmisId=source_row["EmisId"], MoId=source_row["MoId"],
        )
    check("rytem_diff_scope", normalized == base_rytem, "legacy-gas emission ratios for duplicated physical mode only")

    td = one(cand_rytcm["IAR"]["SC_0"], TechId=td_id, CommId=gross_id, MoId=1)
    td_errors = {
        year: float(td[year]) - (build.TD_IAR.get(year, build.TD_IAR["2024"]))
        for year in YEARS
    }
    check("gross_to_sales_equation", max(abs(value) for value in td_errors.values()) < TOL, td_errors)

    rc = one(cand_ryt["RC"]["SC_0"], TechId=old_gas_id)
    base_rc = one(base_ryt["RC"]["SC_0"], TechId=old_gas_id)
    af = one(cand_ryt["AF"]["SC_0"], TechId=old_gas_id)
    base_af = one(base_ryt["AF"]["SC_0"], TechId=old_gas_id)
    capacity_errors, availability_errors = {}, {}
    scale = build.GAS_CAPACITY_2022_GW / float(base_rc["2022"])
    for year in YEARS:
        expected_rc = float(base_rc[year]) * scale if int(year) >= 2022 else float(base_rc[year])
        expected_af = build.GAS_AF_2022_ONWARD if int(year) >= 2022 else float(base_af[year])
        capacity_errors[year] = float(rc[year]) - expected_rc
        availability_errors[year] = float(af[year]) - expected_af
    check(
        "gas_stock_and_availability_equations",
        max(abs(v) for v in capacity_errors.values()) < TOL
        and max(abs(v) for v in availability_errors.values()) < TOL,
        {"capacity_errors": capacity_errors, "availability_errors": availability_errors},
    )
    base_zero_years = [year for year in YEARS if close(base_rc[year], 0.0)]
    cand_zero_years = [year for year in YEARS if close(rc[year], 0.0)]
    check("retirement_years_preserved", base_zero_years == cand_zero_years, {"zero_capacity_years": cand_zero_years})

    gas_iar1 = one(cand_rytcm["IAR"]["SC_0"], TechId=old_gas_id, CommId=gas_id, MoId=1)
    gas_iar2 = one(cand_rytcm["IAR"]["SC_0"], TechId=old_gas_id, CommId=gas_id, MoId=2)
    gas_iar_errors = {}
    for year in YEARS:
        if int(year) < 2022:
            expected = float(one(base_rytcm["IAR"]["SC_0"], TechId=old_gas_id, CommId=gas_id, MoId=1)[year])
        else:
            expected = build.GAS_PLANT_IAR.get(year, build.GAS_PLANT_IAR["2024"])
        gas_iar_errors[year] = {
            "mode1": float(gas_iar1[year]) - (0.0 if int(year) >= 2028 else expected),
            "mode2": float(gas_iar2[year]) - expected,
        }
    check(
        "gas_efficiency_and_market_mode",
        max(abs(v) for row in gas_iar_errors.values() for v in row.values()) < TOL,
        gas_iar_errors,
    )

    vc1 = one(cand_rytm["VC"]["SC_0"], TechId=old_gas_id, MoId=1)
    vc2 = one(cand_rytm["VC"]["SC_0"], TechId=old_gas_id, MoId=2)
    tamul1 = one(cand_rytm["TAMUL"]["SC_0"], TechId=old_gas_id, MoId=1)
    tamul2 = one(cand_rytm["TAMUL"]["SC_0"], TechId=old_gas_id, MoId=2)
    tamll1 = one(cand_rytm["TAMLL"]["SC_0"], TechId=old_gas_id, MoId=1)
    tamll2 = one(cand_rytm["TAMLL"]["SC_0"], TechId=old_gas_id, MoId=2)
    gas_price = one(cand_rytm["VC"]["SC_0"], TechId=extraction_id, MoId=1)
    fc = one(cand_ryt["FC"]["SC_0"], TechId=old_gas_id)
    contract_errors = {}
    for year in YEARS:
        delivered = build.CONTRACT_RAW_PJ.get(year, 0.0)
        plant_iar = (
            build.GAS_PLANT_IAR.get(year, build.GAS_PLANT_IAR["2024"])
            if int(year) >= 2022 else float(gas_iar1[year])
        )
        upstream = build.PROCESS_RAW_PER_DELIVERED * plant_iar
        expected_cap = delivered / plant_iar if delivered else 99999.0
        expected_vc1 = build.VOM - float(gas_price[year]) * upstream if delivered else 0.0
        expected_fc = (
            build.BASE_FIXED_COST
            + delivered * build.PROCESS_RAW_PER_DELIVERED * float(gas_price[year]) / float(rc[year])
            if delivered else build.BASE_FIXED_COST
        )
        contract_errors[year] = {
            "mode1_cap": float(tamul1[year]) - expected_cap,
            "mode2_cap": float(tamul2[year]) - 99999.0,
            "mode1_vc": float(vc1[year]) - expected_vc1,
            "mode2_vc": float(vc2[year]) - build.VOM,
            "fixed_cost": float(fc[year]) - expected_fc,
            "mode1_lower": float(tamll1[year]),
            "mode2_lower": float(tamll2[year]),
        }
    check(
        "capped_contract_cost_reclassification",
        max(abs(v) for row in contract_errors.values() for v in row.values()) < TOL,
        contract_errors,
    )
    check(
        "no_dispatch_floor_or_activity_pin",
        cand_rytm["TAMLL"] == base_rytm["TAMLL"]
        and cand_ryt["TAL"] == base_ryt["TAL"]
        and cand_ryt["TAU"] == base_ryt["TAU"],
        "TAMLL, TAL and TAU are byte-semantically inherited; contract mode has an upper tranche only.",
    )

    extraction_cap = one(cand_ryt["TAU"]["SC_0"], TechId=extraction_id)
    import_cap = one(cand_ryt["TAU"]["SC_0"], TechId=import_id)
    feasibility = {}
    feasible = True
    for year in ("2022", "2023", "2024"):
        plant_iar = build.GAS_PLANT_IAR[year]
        observed_processed = OBSERVED_GAS_PJ[year] * plant_iar
        required_upstream = observed_processed * build.PROCESS_RAW_PER_DELIVERED
        available_upstream = float(extraction_cap[year]) + float(import_cap[year])
        capacity_envelope = float(rc[year]) * float(af[year]) * CAPACITY_TO_ACTIVITY
        upstream_margin = available_upstream - required_upstream
        capacity_margin = capacity_envelope - OBSERVED_GAS_PJ[year]
        feasible = feasible and upstream_margin >= -TOL and capacity_margin >= -TOL
        feasibility[year] = {
            "observed_gas_generation_pj_benchmark": OBSERVED_GAS_PJ[year],
            "plant_processed_gas_required_pj": observed_processed,
            "upstream_gas_required_after_processing_pj": required_upstream,
            "domestic_plus_import_envelope_pj": available_upstream,
            "upstream_margin_before_endogenous_nonpower_use_pj": upstream_margin,
            "legacy_gas_capacity_envelope_pj": capacity_envelope,
            "capacity_margin_pj": capacity_margin,
        }
    check("observed_gas_is_theoretically_feasible_not_forced", feasible, feasibility)

    scenarios = {row["ScenarioId"]: row["Scenario"] for row in cand_gen["osy-scenarios"] if row.get("Active")}
    inherited_policy = {}
    for scenario_id, scenario_name in scenarios.items():
        if scenario_id == "SC_0":
            continue
        inherited_policy[scenario_name] = {
            parameter: cand_ryt[parameter][scenario_id] == base_ryt[parameter][scenario_id]
            for parameter in cand_ryt
            if isinstance(cand_ryt[parameter], dict) and scenario_id in cand_ryt[parameter]
        }
    check(
        "policy_override_rows_unchanged",
        all(all(values.values()) for values in inherited_policy.values()),
        inherited_policy,
    )

    required_ledger_ids = {
        "SOURCES.csv": ("source_id", {
            "SRC_PHL_V36_DOE_ELECTRICITY_BALANCE_2024", "SRC_PHL_V36_DOE_OFFGRID_2020",
            "SRC_PHL_V36_DOE_GAS_CAPACITY_2024", "SRC_PHL_V36_FPH_GAS_CONTRACTS_2024",
            "SRC_PHL_V36_DOE_POWER_INPUT_2023", "SRC_PHL_V36_DOE_POWER_INPUT_2024",
        }),
        "ASSUMPTIONS.csv": ("assumption_id", {
            "ASM_PHL_V36_GRID_BALANCE_BOUNDARY", "ASM_PHL_V36_GAS_STOCK_REMEASUREMENT",
            "ASM_PHL_V36_CONTRACT_COST_RECLASSIFICATION", "ASM_PHL_V36_GAS_PLANT_EFFICIENCY",
        }),
        "CALCULATIONS.csv": ("calculation_id", {
            "CALC_PHL_V36_TD_OWN_USE", "CALC_PHL_V36_GAS_CONTRACT_MODES",
            "CALC_PHL_V36_GAS_STOCK", "CALC_PHL_V36_GAS_PLANT_IAR",
        }),
        "MODEL_MAP.csv": ("map_id", {
            "MAP_PHL_V36_TD_GROSS_TO_SALES", "MAP_PHL_V36_GAS_STOCK",
            "MAP_PHL_V36_GAS_CONTRACT_MODE", "MAP_PHL_V36_GAS_PLANT_EFFICIENCY",
        }),
        "CHANGES.csv": ("change_id", {"CHG_PHL_V36_POWER_GAS_HISTORY"}),
    }
    ledger_detail = {}
    ledger_pass = True
    for filename, (field, required) in required_ledger_ids.items():
        ids = csv_ids(CANDIDATE / "data_sources" / filename, field)
        counts = {identifier: ids.count(identifier) for identifier in required}
        ledger_detail[filename] = counts
        ledger_pass = ledger_pass and all(count == 1 for count in counts.values())
    gaps = csv_ids(CANDIDATE / "data_sources/GAPS.csv", "item")
    required_gaps = {
        "PHL commercial-electricity demand decomposition",
        "PHL gas dispatch regional network and LNG contract detail",
    }
    ledger_detail["GAPS.csv"] = {item: gaps.count(item) for item in required_gaps}
    ledger_pass = ledger_pass and all(gaps.count(item) == 1 for item in required_gaps)
    check("six_table_schema_ledger_complete", ledger_pass, ledger_detail)

    evidence_hashes = {
        filename: sha256(CANDIDATE / "data_sources/evidence/v36_power_gas" / filename)
        for filename in build.EVIDENCE
    }
    check("evidence_hashes_exact", evidence_hashes == build.EVIDENCE, evidence_hashes)
    res_entries = sorted(path.name for path in (CANDIDATE / "res").iterdir())
    check("clean_staging_before_generation", not res_entries, res_entries)

    failure_count = sum(row["status"] == "fail" for row in checks)
    report = {
        "schema": "philippines-v36-power-gas-equation-first-gate-v1",
        "case": str(CANDIDATE),
        "baseline": str(BASELINE),
        "status": "pass_zero_solve" if failure_count == 0 else "fail",
        "failure_count": failure_count,
        "optimizer_runs": 0,
        "generation_runs": 0,
        "observation_classification": {
            "DOE_gross_generation": "benchmark_only",
            "DOE_natural_gas_generation": "benchmark_only",
            "DOE_grid_sales_own_use_and_loss": "physical_conversion_parameter",
            "DOE_gas_nameplate_capacity": "initial_physical_stock",
            "DOE_dependable_capacity": "continuing_physical_availability",
            "DOE_gas_fuel_input": "physical_conversion_efficiency",
            "Santa_Rita_and_San_Lorenzo_TOPQ": "continuing_contractual_cost_and_eligibility_upper_tranche",
            "electricity_final_demands": "genuine_exogenous_final_demand_unchanged_pending_end_use_reconciliation",
        },
        "technology_classification": {
            "PHL_POW_TD": "pass_through_conversion",
            "PHL_POW_CHP_NG_OLD": "physical_conversion_stock_with_two_economic_modes",
            "PHL_PRO_EXTR_NG": "resource_supply",
            "PHL_PRO_IMP_NG": "resource_supply",
            "PHL_PRO_PROC_NG": "fuel_processing_conversion",
        },
        "equation_map": {
            "gross_to_sales": "EBa11_EnergyBalanceEachTS5 production must cover PHL_POW_TD input; IAR converts metered sales activity to gross grid electricity.",
            "gas_capacity": "CAa4_TotalActivityPerYear1 and capacity/activity limits use RC, AF and CapacityToActivityUnit; no activity minimum is introduced.",
            "gas_resource": "AAC2_TotalAnnualTechnologyActivityUpperLimit caps extraction/import supply; PHL_PRO_PROC_NG and plant IAR propagate fuel requirements.",
            "contract": "TAMUL limits only discounted mode 1 eligibility; identical mode 2 keeps dispatch physically available at market cost.",
        },
        "known_unresolved_boundary": "DOE commercial metered sales combine appliance and electric-heat uses while PHL_SER_ELEF excludes endogenous heat. Final demand was not overwritten because doing so would double count an endogenous route.",
        "checks": checks,
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "failure_count": failure_count, "output": str(OUTPUT)}, indent=2))
    if failure_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
