#!/usr/bin/env python3
"""Zero-solve semantic gate for the minimal Philippines v23 biomass repair."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import build_philippines_v23_biomass_simple as spec


TOL = 1e-9


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keyed(rows, *fields):
    return {tuple(row[field] for field in fields): row for row in rows}


def rows_for(table, parameter, tech_id, **filters):
    return [
        row for row in table[parameter][spec.BASE]
        if row.get("TechId") == tech_id
        and all(row.get(field) == value for field, value in filters.items())
    ]


def inherited_null(table, parameter, predicate):
    return all(
        all(row[year] is None for year in spec.YEARS)
        for scenario, rows in table[parameter].items() if scenario != spec.BASE
        for row in rows if predicate(row)
    )


def csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--parent", type=Path, default=spec.SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    parent = args.parent.resolve()
    gen = read_json(candidate / "genData.json")
    parent_gen = read_json(parent / "genData.json")
    tech_id = {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}
    comm_id = {row["Comm"]: row["CommId"] for row in gen["osy-comm"]}
    emis_id = {row["Emis"]: row["EmisId"] for row in gen["osy-emis"]}
    checks = []

    def check(name, passed, detail):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    check("identity", gen["osy-casename"] == "Philippines_v23", gen["osy-casename"])
    check(
        "minimal_structural_delta",
        len(gen["osy-tech"]) == len(parent_gen["osy-tech"]) + 1
        and len(gen["osy-comm"]) == len(parent_gen["osy-comm"])
        and len(gen["osy-constraints"]) == len(parent_gen["osy-constraints"]),
        {"technology_delta": len(gen["osy-tech"]) - len(parent_gen["osy-tech"]), "commodity_delta": len(gen["osy-comm"]) - len(parent_gen["osy-comm"]), "constraint_delta": len(gen["osy-constraints"]) - len(parent_gen["osy-constraints"])},
    )
    forbidden = {
        "PHL_CRP_SUGARCANE_RAW", "PHL_CRP_PADDY_RAW", "PHL_RES_BAGASSE_RAW",
        "PHL_RES_RICE_HUSK_RAW", "PHL_RES_CANE_TRASH_RAW", "PHL_RES_FUELWOOD_RAW",
        "PHL_PRO_CHARCOAL_KILN", "PHL_PRO_GATE_SUGARCANE_RESIDUE",
        "PHL_PRO_GATE_PADDY_RESIDUE", "PHL_PRO_COL_BAGASSE_PWR",
    }
    check("detailed_formulation_absent", not forbidden.intersection(tech_id | comm_id), sorted(forbidden.intersection(tech_id | comm_id)))
    check("founding_processor_reclassified", "PHL_PRO_PROC_BIOM" not in tech_id and tech_id.get("PHL_PRO_SUP_GENERIC_BIOMASS") == "TEC_telf6", tech_id.get("PHL_PRO_SUP_GENERIC_BIOMASS"))

    ryt = read_json(candidate / "RYT.json")
    rt = read_json(candidate / "RT.json")
    rytm = read_json(candidate / "RYTM.json")
    rytcm = read_json(candidate / "RYTCM.json")
    rytts = read_json(candidate / "RYTTs.json")
    rytem = read_json(candidate / "RYTEM.json")
    base_ryt = {parameter: keyed(ryt[parameter][spec.BASE], "TechId") for parameter in ("RC", "TAMaxC", "TAMaxCI", "TAU", "TAL", "AF")}
    supply_detail = {}
    supply_ok = True
    for name, cap in (("PHL_PRO_SUP_GENERIC_BIOMASS", spec.GENERIC_CAP_PJ), (spec.RESIDUE_TECH, spec.RESIDUE_CAP_PJ)):
        tid = tech_id[name]
        capacity_stock = spec.nonbinding_capacity_stock(cap)
        supply_detail[name] = {"annual_cap": cap, "capacity_stock": capacity_stock, "cau": rt["CAU"][spec.BASE][0][tid]}
        for year in spec.YEARS:
            supply_ok &= abs(float(base_ryt["RC"][(tid,)][year]) - capacity_stock) < TOL
            supply_ok &= abs(float(base_ryt["TAMaxC"][(tid,)][year]) - capacity_stock) < TOL
            supply_ok &= abs(float(base_ryt["TAU"][(tid,)][year]) - cap) < TOL
            supply_ok &= float(base_ryt["TAMaxCI"][(tid,)][year]) == 0.0
            supply_ok &= float(base_ryt["TAL"][(tid,)][year]) == 0.0
            supply_ok &= float(base_ryt["AF"][(tid,)][year]) == 1.0
        supply_ok &= abs(float(rt["CAU"][spec.BASE][0][tid]) - spec.STANDARD_CAPACITY_TO_ACTIVITY) < TOL
        supply_ok &= abs(capacity_stock * float(rt["CAU"][spec.BASE][0][tid]) - cap / spec.MIN_YEAR_SPLIT) < TOL
        supply_ok &= float(rt["OL"][spec.BASE][0][tid]) == 1.0
        supply_ok &= inherited_null(ryt, "TAU", lambda row, tid=tid: row["TechId"] == tid)
        supply_ok &= inherited_null(ryt, "RC", lambda row, tid=tid: row["TechId"] == tid)
        supply_ok &= inherited_null(rytts, "CF", lambda row, tid=tid: row["TechId"] == tid)
    check("finite_nonforcing_supply_boundaries", supply_ok, supply_detail)

    generic = tech_id["PHL_PRO_SUP_GENERIC_BIOMASS"]
    residue = tech_id[spec.RESIDUE_TECH]
    generic_oar = rows_for(rytcm, "OAR", generic, CommId=comm_id["PHL_PRO_BIOM"])
    residue_fit = rows_for(rytcm, "OAR", residue, CommId=comm_id["PHL_PRO_BIOM_FIT_RESIDUE"])
    residue_generic = rows_for(rytcm, "OAR", residue, CommId=comm_id["PHL_PRO_BIOM"])
    mapping_ok = all(
        all(abs(float(row[y]) - (1.0 if row["MoId"] == mode else 0.0)) < TOL for y in spec.YEARS)
        for rows, mode in ((generic_oar, 1), (residue_fit, 1), (residue_generic, 2)) for row in rows
    )
    mapping_ok &= len(generic_oar) == 30 and len(residue_fit) == 30 and len(residue_generic) == 30
    check("minimal_supply_output_modes", mapping_ok, "generic m1; shared residue-to-CHP m1; residue-to-generic m2")

    price_ok = True
    for tid, modes in ((generic, {1: spec.GENERIC_COST}), (residue, {1: spec.RESIDUE_COST, 2: spec.RESIDUE_COST})):
        for row in rows_for(rytm, "VC", tid):
            expected = modes.get(row["MoId"], 0.0)
            price_ok &= all(abs(float(row[y]) - expected) < TOL for y in spec.YEARS)
    check("sourced_supply_costs", price_ok, {"generic": spec.GENERIC_COST, "residue": spec.RESIDUE_COST})

    chp_ok = True
    for name in ("PHL_POW_CHP_BIOM_OLD", "PHL_POW_CHP_BIOM_FIT_OLD"):
        rows = rows_for(rytcm, "IAR", tech_id[name], CommId=comm_id["PHL_PRO_BIOM_FIT_RESIDUE"])
        chp_ok &= len(rows) == 30
        for row in rows:
            chp_ok &= all(abs(float(row[y]) - (4.000666667 if row["MoId"] == 1 else 0.0)) < TOL for y in spec.YEARS)
    check("common_legacy_chp_residue_pool", chp_ok, "both slices consume PHL_PRO_BIOM_FIT_RESIDUE at IAR 4.000666667")

    charcoal = tech_id["PHL_HOU_COOK_CHARCOAL_OLD"]
    char_iar = rows_for(rytcm, "IAR", charcoal, CommId=comm_id["PHL_PRO_BIOM"])
    char_ok = len(char_iar) == 30 and all(
        all(abs(float(row[y]) - (spec.CHARCOAL_ROUTE_IAR if row["MoId"] == 1 else 0.0)) < TOL for y in spec.YEARS)
        for row in char_iar
    )
    expected_emissions = {
        emis_id["CO2e"]: spec.KILN_CO2E_PER_USEFUL_PJ,
        emis_id["PM2_5"]: spec.CHARCOAL_STOVE_PM25_PER_USEFUL_PJ + spec.KILN_PM25_PER_USEFUL_PJ,
    }
    for emission, factor in expected_emissions.items():
        rows = rows_for(rytem, "EAR", charcoal, EmisId=emission)
        char_ok &= len(rows) == 30
        for row in rows:
            char_ok &= all(abs(float(row[y]) - (factor if row["MoId"] == 1 else 0.0)) < TOL for y in spec.YEARS)
    check("integrated_closed_charcoal_route", char_ok, {"iar": spec.CHARCOAL_ROUTE_IAR, "emissions": expected_emissions})

    ryc = read_json(candidate / "RYC.json")
    parent_ryc = read_json(parent / "RYC.json")
    parent_ryt = read_json(parent / "RYT.json")
    parent_tid = {row["Tech"]: row["TechId"] for row in parent_gen["osy-tech"]}
    cooking_ok = True
    for parameter in ("SAD", "AAD"):
        cand = next(row for row in ryc[parameter][spec.BASE] if row["CommId"] == comm_id["PHL_HOU_COOK"])
        old = next(row for row in parent_ryc[parameter][spec.BASE] if row["CommId"] == comm_id["PHL_HOU_COOK"])
        cooking_ok &= all(abs(float(cand[y]) - float(old[y]) * spec.COOKING_SCALE) < TOL for y in spec.YEARS)
    for old_name in ("PHL_HOU_COOK_OIL", "PHL_HOU_COOK_ELE", "PHL_HOU_COOK_NG", "PHL_HOU_COOK_COAL", "PHL_HOU_COOK_BIOM"):
        new_name = "PHL_HOU_COOK_CHARCOAL_OLD" if old_name == "PHL_HOU_COOK_COAL" else old_name
        for parameter in ("RC", "TAMaxCI"):
            cand = next(row for row in ryt[parameter][spec.BASE] if row["TechId"] == tech_id[new_name])
            old = next(row for row in parent_ryt[parameter][spec.BASE] if row["TechId"] == parent_tid[old_name])
            cooking_ok &= all(abs(float(cand[y]) - float(old[y]) * spec.COOKING_SCALE) < TOL for y in spec.YEARS)
    check("cooking_final_to_useful_repair", cooking_ok, {"useful_2020_pj": spec.COOKING_USEFUL_2020_PJ, "scale": spec.COOKING_SCALE})

    # The simplification must not modify crop/land activity coefficients or add a UDC.
    land_ids = {row["TechId"] for row in parent_gen["osy-tech"] if row["Tech"].startswith("LND") or row["Tech"] == "ENV_LAND"}
    parent_rytcm = read_json(parent / "RYTCM.json")
    untouched_land = True
    for parameter in ("IAR", "OAR"):
        cand = keyed([row for row in rytcm[parameter][spec.BASE] if row["TechId"] in land_ids], "TechId", "CommId", "MoId")
        old = keyed([row for row in parent_rytcm[parameter][spec.BASE] if row["TechId"] in land_ids], "TechId", "CommId", "MoId")
        untouched_land &= cand == old
    check("crop_and_land_coefficients_untouched", untouched_land, f"{len(land_ids)} land technologies compared exactly")
    check("no_new_user_defined_constraint", gen["osy-constraints"] == parent_gen["osy-constraints"], len(gen["osy-constraints"]))

    reports = {
        "base": "biomass_generic_gate_base.json", "coal_phaseout": "biomass_generic_gate_coal_phaseout.json",
        "re": "biomass_generic_gate_re.json", "ev": "biomass_generic_gate_ev.json",
    }
    gate_status = {}
    for name, filename in reports.items():
        path = candidate / "documentation" / filename
        data = read_json(path) if path.is_file() else {}
        gate_status[name] = data.get("status", "missing")
    check("generic_gate_all_scenarios", all(value == "passed_no_deterministic_contradiction" for value in gate_status.values()), gate_status)

    parent_hashes = {path.name: sha256(path) for path in parent.glob("*.json")}
    changed = sorted(path.name for path in candidate.glob("*.json") if parent_hashes.get(path.name) != sha256(path))
    allow = {"genData.json", "RT.json", "RYT.json", "RYTM.json", "RYTCM.json", "RYTTs.json", "RYC.json", "RYTEM.json", "RYTCn.json"}
    check("source_diff_allowlist", set(changed) <= allow, changed)

    ledger = candidate / "data_sources"
    required = {
        "SOURCES.csv": {"SRC_PHL_V23_BIOMASS_IRENA_SUPPLY", "SRC_PHL_V23_BIOMASS_DOE_AWARDED_2025"},
        "ASSUMPTIONS.csv": {"ASM_PHL_V23_BIOMASS_SIMPLE_FLAT_CAP", "ASM_PHL_V23_BIOMASS_SIMPLE_NONFORCING"},
        "CALCULATIONS.csv": {"CALC_PHL_V23_BIOMASS_SIMPLE_RESIDUE_CAP", "CALC_PHL_V23_BIOMASS_SIMPLE_GENERIC_CAP", "CALC_PHL_V23_BIOMASS_SIMPLE_COSTS"},
        "MODEL_MAP.csv": {"MAP_PHL_V23_BIOMASS_SIMPLE_GENERIC", "MAP_PHL_V23_BIOMASS_SIMPLE_RESIDUE", "MAP_PHL_V23_BIOMASS_SIMPLE_CHP"},
        "GAPS.csv": {"Endogenous crop/forest biomass availability", "Separate generated, collected and uncollected biomass reporting"},
        "CHANGES.csv": {"CHG_PHL_V23_BIOMASS_SIMPLE_20260824"},
    }
    ledger_detail = {}
    ledger_ok = True
    for filename, wanted in required.items():
        rows = csv_rows(ledger / filename)
        key = next(iter(rows[0]))
        values = [row[key] for row in rows]
        missing = sorted(wanted - set(values))
        ledger_ok &= not missing and len(values) == len(set(values))
        ledger_detail[filename] = {"rows": len(rows), "missing": missing}
    source_ids = {row["source_id"] for row in csv_rows(ledger / "SOURCES.csv")}
    assumption_ids = {row["assumption_id"] for row in csv_rows(ledger / "ASSUMPTIONS.csv")}
    calculation_ids = {row["calculation_id"] for row in csv_rows(ledger / "CALCULATIONS.csv")}
    def evidence_tokens(value):
        # The cumulative ledger contains both historical space-separated and
        # current semicolon-separated evidence lists.
        return [item for item in re.split(r"[;\s]+", value.strip()) if item]

    for row in csv_rows(ledger / "ASSUMPTIONS.csv"):
        ledger_ok &= all(item in source_ids for item in evidence_tokens(row["evidence_source_ids"]))
    for row in csv_rows(ledger / "CALCULATIONS.csv"):
        ledger_ok &= all(item in source_ids for item in evidence_tokens(row["source_ids"]))
        ledger_ok &= all(item in assumption_ids for item in evidence_tokens(row["assumption_ids"]))
    for row in csv_rows(ledger / "MODEL_MAP.csv"):
        ledger_ok &= all(item in source_ids | assumption_ids | calculation_ids for item in evidence_tokens(row["evidence_ids"]))
    check("six_table_schema_ledger_and_references", ledger_ok, ledger_detail)
    founding_absent = all(
        all(abs(float(row[y]) - bad) > TOL for y in spec.YEARS for bad in (16.0, 3.9493417760415483))
        for row in rows_for(rytm, "VC", generic)
    )
    check("founding_biomass_prices_absent", founding_absent, {"generic": spec.GENERIC_COST, "residue": spec.RESIDUE_COST})

    failures = [item for item in checks if not item["passed"]]
    report = {
        "schema": "philippines-v23-biomass-simple-deterministic-gate-v1", "candidate": str(candidate), "parent": str(parent),
        "status": "passed" if not failures else "failed", "optimizer_runs": 0, "model_generation_runs": 0,
        "checks": checks, "failure_count": len(failures), "failures": failures,
        "next_step": "application generation and preprocessing" if not failures else "repair source candidate before generation",
    }
    payload = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
