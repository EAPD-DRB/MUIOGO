#!/usr/bin/env python3
"""Replace dispatch-valued FIT revenue with physical biomass cost accounting."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import types
from datetime import date
from pathlib import Path
from typing import Any


YEARS = [str(year) for year in range(2020, 2054)]
FIT_TECH = "TEC_v21bio"
ORDINARY_BIOMASS_TECH = "TEC_gthhk"
BIOMASS_SUPPLY_TECH = "TEC_telf6"
GENERIC_BIOMASS = "COM_0"
FIT_BIOMASS = "COM_v22fit"
RENEWABLES = "CO_xr1eb"
FIT_IAR = 4.000666667
COLLECTION_COST_PER_ELECTRICITY = 15.8
COLLECTION_COST_PER_BIOMASS = COLLECTION_COST_PER_ELECTRICITY / FIT_IAR


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".codex-tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(payload: dict, parameter: str, technology: str | None = None,
        commodity: str | None = None, *, scenario: str = "SC_0", **keys: Any) -> dict:
    matches = [item for item in payload[parameter][scenario]
               if (technology is None or item.get("TechId") == technology)
               and (commodity is None or item.get("CommId") == commodity)
               and all(item.get(key) == value for key, value in keys.items())]
    if len(matches) != 1:
        raise AssertionError((parameter, scenario, technology, commodity, keys, len(matches)))
    return matches[0]


def append_ledger(path: Path, key: str, values: dict[str, str]) -> None:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if not fieldnames or key not in values:
        raise AssertionError((path, key, fieldnames, values))
    identifiers = {item[key] for item in rows}
    if values[key] in identifiers:
        raise AssertionError(f"duplicate ledger identifier {values[key]} in {path}")
    unknown = set(values) - set(fieldnames)
    if unknown:
        raise AssertionError((path, unknown))
    rows.append({name: values.get(name, "") for name in fieldnames})
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def update_structure(case: Path, muiogo: Path) -> None:
    gen = read(case / "genData.json")
    assert gen["osy-casename"] == "Philippines_v22"
    assert FIT_BIOMASS not in {item["CommId"] for item in gen["osy-comm"]}
    technologies = {item["TechId"]: item for item in gen["osy-tech"]}
    fit = technologies[FIT_TECH]
    supply = technologies[BIOMASS_SUPPLY_TECH]
    ordinary = technologies[ORDINARY_BIOMASS_TECH]
    assert set(fit["IAR"]) == {"COM_viggz", GENERIC_BIOMASS}
    assert supply["OAR"] == [GENERIC_BIOMASS]
    assert ordinary["OAR"] == fit["OAR"]
    renewable = next(item for item in gen["osy-constraints"] if item["ConId"] == RENEWABLES)
    assert ORDINARY_BIOMASS_TECH in renewable["CM"] and FIT_TECH not in renewable["CM"]

    gen["osy-comm"].append({
        "CommId": FIT_BIOMASS,
        "Comm": "PHL_PRO_BIOM_FIT_RESIDUE",
        "Desc": "Crop-residue biomass collected for the closed legacy FIT biomass tranche.",
        "UnitId": "PJ",
    })
    supply["OAR"].append(FIT_BIOMASS)
    fit["IAR"] = [FIT_BIOMASS if commodity == GENERIC_BIOMASS else commodity
                  for commodity in fit["IAR"]]
    fit["Desc"] = (
        "Closed 250 MW DOE FIT-eligible biomass tranche using crop-derived residue ceiling; "
        "the optimizer includes physical collection cost while tariff cash flow is published post-solve."
    )
    renewable["CM"].append(FIT_TECH)
    gen["osy-desc"] = (
        "FIT-accounting correction: the closed biomass FIT tranche uses a dedicated physical "
        "residue-supply mode at positive collection cost. Feed-in-tariff payments are excluded "
        "from the national resource-cost objective and disclosed post-solve; no activity, build, "
        "dispatch or share outcome is forced.\n\n" + gen.get("osy-desc", "")
    )

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *unused_args, **unused_kwargs: None
    sys.modules.setdefault("dotenv", dotenv_stub)
    sys.path.insert(0, str(muiogo / "API"))
    from Classes.Base.FileClass import File
    from Classes.Case.UpdateCaseClass import UpdateCase
    UpdateCase(case.name, gen).updateCase()
    File.writeFile(gen, case / "genData.json")


def update_parameters(case: Path) -> None:
    rytcm = read(case / "RYTCM.json")
    supply_output = row(rytcm, "OAR", BIOMASS_SUPPLY_TECH, FIT_BIOMASS, MoId=2)
    fit_input = row(rytcm, "IAR", FIT_TECH, FIT_BIOMASS, MoId=1)
    for year in YEARS:
        supply_output[year] = 1.0
        fit_input[year] = FIT_IAR
    write(case / "RYTCM.json", rytcm)

    rytm = read(case / "RYTM.json")
    supply_cost = row(rytm, "VC", BIOMASS_SUPPLY_TECH, MoId=2)
    fit_cost = row(rytm, "VC", FIT_TECH, MoId=1)
    for year in YEARS:
        supply_cost[year] = COLLECTION_COST_PER_BIOMASS
        fit_cost[year] = 0.0001
    write(case / "RYTM.json", rytm)

    rytcn = read(case / "RYTCn.json")
    for parameter in ("CAM", "CCM", "CNCM"):
        for scenario in rytcn[parameter]:
            source = row(rytcn, parameter, ORDINARY_BIOMASS_TECH,
                         scenario=scenario, ConId=RENEWABLES)
            target = row(rytcn, parameter, FIT_TECH,
                         scenario=scenario, ConId=RENEWABLES)
            for year in YEARS:
                target[year] = source[year]
    write(case / "RYTCn.json", rytcn)


def update_ledger(case: Path) -> None:
    ledger = case / "data_sources"
    append_ledger(ledger / "SOURCES.csv", "source_id", {
        "source_id": "SRC_PHL_ERC_BIOMASS_FIT",
        "provider": "Philippines Energy Regulatory Commission",
        "product": "Biomass feed-in tariff resolutions and 2021-2025 adjustment notice",
        "edition": "2012-2025", "reference_period": "2020-2025", "geography": "Philippines",
        "variable": "Biomass FIT rate and 250 MW installation target", "source_unit": "PHP/kWh;MW",
        "exact_locator": "Resolution 10/2012, Resolution 06/2020 and adjusted biomass entrant rates",
        "url": "https://www.erc.gov.ph/Files/Render/issuance/30680", "access_date": "2026-08-20",
        "license": "Philippines government publication",
        "notes": "FIT defines eligibility and post-solve cash flow; it does not require activity and is not a national resource cost.",
    })
    append_ledger(ledger / "ASSUMPTIONS.csv", "assumption_id", {
        "assumption_id": "ASM_PHL_V22_FIT_RESOURCE_COST_BOUNDARY",
        "statement": "Biomass FIT payments are domestic transfers, not resource costs; the optimizer retains residue collection cost and publishes tariff cash flow post-solve.",
        "central_value": "15.8", "unit": "MUSD/PJ electricity",
        "evidence_source_ids": "SRC_PHL_ERC_BIOMASS_FIT",
        "rationale": "Prevents a policy transfer from becoming a dispatch subsidy while retaining the physical cost driver and closed eligible stock.",
        "notes": "The 15.8 value is inherited from v21's ERC-anchored residue collection assumption; it is not calibrated to generation.",
    })
    append_ledger(ledger / "CALCULATIONS.csv", "calculation_id", {
        "calculation_id": "CALC_PHL_V22_FIT_RESIDUE_SUPPLY_COST",
        "formula": "dedicated residue supply VC = 15.8 / 4.000666667; FIT plant VC = 0.0001",
        "source_ids": "SRC_PHL_ERC_BIOMASS_FIT",
        "assumption_ids": "ASM_PHL_V22_FIT_RESOURCE_COST_BOUNDARY",
        "input_values": "15.8;4.000666667", "input_units": "MUSD/PJ electricity;PJ biomass/PJ electricity",
        "output_value": f"{COLLECTION_COST_PER_BIOMASS:.16g}", "output_unit": "MUSD/PJ biomass",
        "script_path": "scripts/apply_philippines_v22_fit_accounting.py", "script_version": "r9",
        "notes": "Tariff rates are applied only to solved FIT electricity in the post-solve publication.",
    })
    append_ledger(ledger / "MODEL_MAP.csv", "map_id", {
        "map_id": "MAP_PHL_V22_FIT_PHYSICAL_ACCOUNTING",
        "model_file": "genData.json;RYTCM.json;RYTM.json",
        "parameter": "commodity membership;IAR;OAR;VC",
        "entity": "COM_v22fit;TEC_telf6 mode 2;TEC_v21bio mode 1", "mode": "1;2",
        "scenario": "SC_0 with inheritance", "years": "2020-2053",
        "value_or_expression": "OAR=1;IAR=4.000666667;supply VC=15.8/IAR;plant VC=0.0001",
        "model_unit": "PJ;MUSD/PJ", "evidence_ids": "CALC_PHL_V22_FIT_RESIDUE_SUPPLY_COST",
        "evidence_type": "derived physical parameter",
        "notes": "One dedicated commodity and one existing-technology mode; no technology, demand, bound or UDC is added.",
    })
    append_ledger(ledger / "MODEL_MAP.csv", "map_id", {
        "map_id": "MAP_PHL_V22_FIT_RENEWABLE_MEMBERSHIP",
        "model_file": "genData.json;RYTCn.json", "parameter": "CM;CAM",
        "entity": "TEC_v21bio in CO_xr1eb / RENEWABLES", "mode": "all active activity",
        "scenario": "RE", "years": "2020-2053",
        "value_or_expression": "CAM copied exactly from physical twin TEC_gthhk",
        "model_unit": "share-row coefficient", "evidence_ids": "SRC_PHL_ERC_BIOMASS_FIT",
        "evidence_type": "technology classification",
        "notes": "Corrects an omission in the existing policy definition; no new UDC or target is created.",
    })
    append_ledger(ledger / "MODEL_MAP.csv", "map_id", {
        "map_id": "MAP_PHL_V22_FIT_POSTSOLVE_CASHFLOW",
        "model_file": "res/<run>/fit_cashflow_postsolve.csv", "parameter": "published accounting",
        "entity": "TEC_v21bio / PHL_POW_CHP_BIOM_FIT_OLD", "mode": "1",
        "scenario": "each validated run", "years": "2020-2034",
        "value_or_expression": "solved annual activity * applicable FIT rate converted at documented FX",
        "model_unit": "MUSD/year", "evidence_ids": "SRC_PHL_ERC_BIOMASS_FIT",
        "evidence_type": "post-solve disclosure",
        "notes": "Not included in objective, constraints or demand balances.",
    })
    append_ledger(ledger / "GAPS.csv", "item", {
        "item": "FIT incidence and financing",
        "why_absent": "The model has no household tariff, utility revenue or public-finance account, so a domestic feed-in-tariff transfer has no modeled payer.",
        "upgrade_source": "Add an explicit distributional or fiscal account before treating FIT payments as welfare costs or revenues.",
        "priority": "medium",
        "notes": "Current runs publish gross generator receipts post-solve and retain only physical residue cost in the optimizer.",
    })
    append_ledger(ledger / "CHANGES.csv", "change_id", {
        "change_id": "CHG_PHL_V22_FIT_ACCOUNTING_R9_20260820", "date": str(date.today()), "class": "B",
        "description": "Replaced negative dispatch-valued biomass FIT revenue with positive physical residue collection cost, corrected FIT renewable membership, and moved tariff receipts to post-solve disclosure.",
        "model_objects": "genData.json;RYTCM.json;RYTM.json;RYTCn.json;COM_v22fit;TEC_telf6 mode 2;TEC_v21bio",
        "evidence_path": "documentation/MODEL_FIXES_FIT_ACCOUNTING_V22_2026-08-20.md;documentation/fit_accounting_r9_build_manifest.json",
        "map_rows_affected": "MAP_PHL_V22_FIT_PHYSICAL_ACCOUNTING;MAP_PHL_V22_FIT_RENEWABLE_MEMBERSHIP;MAP_PHL_V22_FIT_POSTSOLVE_CASHFLOW",
        "resolve_status": "candidate_pending_four_scenario_validation", "author": "Codex",
        "notes": "No activity, dispatch, build or generation outcome is fixed; no new UDC or technology is added.",
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("--muiogo", type=Path, required=True)
    args = parser.parse_args()
    case, muiogo = args.case.resolve(), args.muiogo.resolve()

    source_files = sorted(case.glob("*.json"))
    before = {path.name: digest(path) for path in source_files}
    update_structure(case, muiogo)
    update_parameters(case)
    update_ledger(case)
    after = {path.name: digest(path) for path in source_files}
    changed = sorted(name for name in before if before[name] != after[name])
    # UpdateCase also adds zero/default demand-profile rows for the new
    # commodity and rewrites two semantically unchanged timeslice files.
    expected = {"genData.json", "RYC.json", "RYCTs.json", "RYTCM.json",
                "RYTCn.json", "RYTM.json", "RYTs.json", "RYTTs.json"}
    if set(changed) != expected:
        raise AssertionError((changed, sorted(expected)))

    manifest = {
        "schema": "philippines-v22-fit-accounting-r9-build-v1",
        "case": str(case), "date": str(date.today()),
        "changed_source_files": changed, "before_sha256": before, "after_sha256": after,
        "objects_added": {"technologies": 0, "commodities": 1, "constraints": 0,
                          "active_existing_technology_modes": 1},
        "classification": {
            "FIT_250_MW": "continuing contractual eligibility applied to an inherited closed physical stock",
            "residue_collection_cost": "physical economic driver",
            "tariff_payment": "domestic transfer published post-solve",
            "generation_and_dispatch": "endogenous benchmark-only outcomes",
        },
        "physical_cost_identity": {
            "fit_iar": FIT_IAR,
            "collection_cost_musd_per_pj_electricity": COLLECTION_COST_PER_ELECTRICITY,
            "supply_vc_musd_per_pj_biomass": COLLECTION_COST_PER_BIOMASS,
            "reconstructed_cost": COLLECTION_COST_PER_BIOMASS * FIT_IAR,
        },
        "no_forcing": ["no activity bound added", "no generation target added", "no dispatch share added",
                       "no build requirement added", "no new user-defined constraint added"],
        "promotion_rule": "BASE must solve first; only then COAL_PHASEOUT, RE and EV run concurrently; all four must be optimal from these exact source hashes.",
    }
    write(case / "documentation" / "fit_accounting_r9_build_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
