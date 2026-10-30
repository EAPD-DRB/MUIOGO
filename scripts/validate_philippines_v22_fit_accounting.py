#!/usr/bin/env python3
"""Deterministic pre-solve gate for the Philippines v22 FIT repair."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


YEARS = [str(year) for year in range(2020, 2054)]
FIT_TECH = "TEC_v21bio"
ORDINARY_TECH = "TEC_gthhk"
SUPPLY_TECH = "TEC_telf6"
FIT_COMM = "COM_v22fit"
RENEWABLES = "CO_xr1eb"
FIT_IAR = 4.000666667
SUPPLY_VC = 15.8 / FIT_IAR
EXPECTED_CHANGED_JSON = {"genData.json", "RYC.json", "RYCTs.json", "RYTCM.json",
                         "RYTCn.json", "RYTM.json", "RYTs.json", "RYTTs.json"}


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(payload: dict, parameter: str, *, scenario: str = "SC_0", **keys: Any) -> list[dict]:
    return [item for item in payload[parameter][scenario]
            if all(item.get(key) == value for key, value in keys.items())]


def one(payload: dict, parameter: str, *, scenario: str = "SC_0", **keys: Any) -> dict:
    found = rows(payload, parameter, scenario=scenario, **keys)
    if len(found) != 1:
        raise AssertionError((parameter, scenario, keys, len(found)))
    return found[0]


def ledger_has(path: Path, key: str, expected: set[str]) -> bool:
    with path.open(newline="", encoding="utf-8") as stream:
        actual = {row[key] for row in csv.DictReader(stream)}
    return expected <= actual


def existing_rows_preserved(old: dict, new: dict) -> tuple[bool, list[dict]]:
    """Compare parameter rows by coordinates while tolerating new default rows."""
    year_keys = set(YEARS)
    additions: list[dict] = []
    for parameter in old:
        for scenario in old[parameter]:
            def coordinate(item: dict) -> tuple:
                return tuple(sorted((key, json.dumps(value, sort_keys=True))
                                    for key, value in item.items() if key not in year_keys))
            before = {coordinate(item): item for item in old[parameter][scenario]}
            after = {coordinate(item): item for item in new[parameter][scenario]}
            if not set(before) <= set(after):
                return False, additions
            if any(before[key] != after[key] for key in before):
                return False, additions
            additions.extend(after[key] for key in set(after) - set(before))
    return True, additions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("control", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    control, candidate = args.control.resolve(), args.candidate.resolve()

    control_json = {path.name: sha(path) for path in control.glob("*.json")}
    candidate_json = {path.name: sha(path) for path in candidate.glob("*.json")}
    changed = {name for name in control_json if control_json[name] != candidate_json[name]}
    checks: dict[str, bool] = {
        "source_diff_allowlist": changed == EXPECTED_CHANGED_JSON,
        "source_file_set_unchanged": set(control_json) == set(candidate_json),
    }

    old_gen, new_gen = read(control / "genData.json"), read(candidate / "genData.json")
    old_tech = {item["TechId"]: item for item in old_gen["osy-tech"]}
    new_tech = {item["TechId"]: item for item in new_gen["osy-tech"]}
    old_comm = {item["CommId"]: item for item in old_gen["osy-comm"]}
    new_comm = {item["CommId"]: item for item in new_gen["osy-comm"]}
    old_constraints = {item["ConId"]: item for item in old_gen["osy-constraints"]}
    new_constraints = {item["ConId"]: item for item in new_gen["osy-constraints"]}
    checks.update({
        "no_technology_added_or_removed": set(old_tech) == set(new_tech),
        "one_dedicated_commodity_added": set(new_comm) - set(old_comm) == {FIT_COMM}
            and not (set(old_comm) - set(new_comm)),
        "no_constraint_added_or_removed": set(old_constraints) == set(new_constraints),
        "fit_input_replaced_not_added": set(new_tech[FIT_TECH]["IAR"])
            == (set(old_tech[FIT_TECH]["IAR"]) - {"COM_0"}) | {FIT_COMM},
        "supply_output_added": set(new_tech[SUPPLY_TECH]["OAR"])
            == set(old_tech[SUPPLY_TECH]["OAR"]) | {FIT_COMM},
        "fit_added_to_existing_renewable_definition":
            set(new_constraints[RENEWABLES]["CM"])
            == set(old_constraints[RENEWABLES]["CM"]) | {FIT_TECH},
    })

    old_rytcm, new_rytcm = read(control / "RYTCM.json"), read(candidate / "RYTCM.json")
    old_rytm, new_rytm = read(control / "RYTM.json"), read(candidate / "RYTM.json")
    old_rytcn, new_rytcn = read(control / "RYTCn.json"), read(candidate / "RYTCn.json")
    fit_input = one(new_rytcm, "IAR", TechId=FIT_TECH, CommId=FIT_COMM, MoId=1)
    supply_output = one(new_rytcm, "OAR", TechId=SUPPLY_TECH, CommId=FIT_COMM, MoId=2)
    fit_cost = one(new_rytm, "VC", TechId=FIT_TECH, MoId=1)
    supply_cost = one(new_rytm, "VC", TechId=SUPPLY_TECH, MoId=2)
    checks.update({
        "fit_dedicated_iar_exact": all(fit_input[year] == FIT_IAR for year in YEARS),
        "dedicated_supply_oar_exact": all(supply_output[year] == 1.0 for year in YEARS),
        "fit_plant_variable_cost_nonnegative": all(fit_cost[year] == 0.0001 for year in YEARS),
        "physical_supply_cost_exact": all(abs(supply_cost[year] - SUPPLY_VC) < 1e-12 for year in YEARS),
        "physical_cost_identity": abs(SUPPLY_VC * FIT_IAR - 15.8) < 1e-12,
        "old_generic_fit_input_removed": not rows(new_rytcm, "IAR", TechId=FIT_TECH, CommId="COM_0"),
        "dedicated_commodity_has_one_positive_producer_mode":
            sum(any((item.get(year) or 0) > 0 for year in YEARS)
                for item in new_rytcm["OAR"]["SC_0"] if item["CommId"] == FIT_COMM) == 1,
        "dedicated_commodity_has_one_positive_consumer_mode":
            sum(any((item.get(year) or 0) > 0 for year in YEARS)
                for item in new_rytcm["IAR"]["SC_0"] if item["CommId"] == FIT_COMM) == 1,
    })

    # The existing supply route has ample annual build/activity ceilings. This
    # prevents the accounting link itself from creating a deterministic demand
    # shortfall; optimization still decides all activity.
    ryt = read(candidate / "RYT.json")
    supply_tamaxci = one(ryt, "TAMaxCI", TechId=SUPPLY_TECH)
    supply_tau = one(ryt, "TAU", TechId=SUPPLY_TECH)
    fit_tau = one(ryt, "TAU", TechId=FIT_TECH)
    checks["new_link_has_deterministic_annual_headroom"] = all(
        supply_tamaxci[year] >= 999999 and supply_tau[year] >= FIT_IAR * fit_tau[year]
        for year in YEARS
    )

    for parameter in ("CAM", "CCM", "CNCM"):
        for scenario in new_rytcn[parameter]:
            source = one(new_rytcn, parameter, scenario=scenario,
                         TechId=ORDINARY_TECH, ConId=RENEWABLES)
            target = one(new_rytcn, parameter, scenario=scenario,
                         TechId=FIT_TECH, ConId=RENEWABLES)
            checks[f"renewable_{parameter}_{scenario}_copied"] = all(
                target[year] == source[year] for year in YEARS
            )

    ryc_preserved, ryc_additions = existing_rows_preserved(
        read(control / "RYC.json"), read(candidate / "RYC.json"))
    rycts_preserved, rycts_additions = existing_rows_preserved(
        read(control / "RYCTs.json"), read(candidate / "RYCTs.json"))
    checks.update({
        "all_existing_demands_preserved": ryc_preserved,
        "all_existing_demand_profiles_preserved": rycts_preserved,
        "new_commodity_has_no_final_demand": bool(ryc_additions) and all(
            item.get("CommId") == FIT_COMM
            and all(item[year] in (0, None) for year in YEARS) for item in ryc_additions
        ),
        "new_commodity_has_only_default_demand_profiles": bool(rycts_additions) and all(
            item.get("CommId") == FIT_COMM
            and all(item[year] in (0, None) for year in YEARS) for item in rycts_additions
        ),
        "bounds_and_capacity_parameters_unchanged": sha(control / "RYT.json") == sha(candidate / "RYT.json"),
        "timeslice_values_semantically_unchanged":
            read(control / "RYTs.json") == read(candidate / "RYTs.json")
            and read(control / "RYTTs.json") == read(candidate / "RYTTs.json"),
        "technology_scalar_parameters_unchanged": sha(control / "RT.json") == sha(candidate / "RT.json"),
    })
    checks.update({
        "ledger_source_present": ledger_has(candidate / "data_sources" / "SOURCES.csv", "source_id",
                                             {"SRC_PHL_ERC_BIOMASS_FIT"}),
        "ledger_assumption_present": ledger_has(candidate / "data_sources" / "ASSUMPTIONS.csv", "assumption_id",
                                                 {"ASM_PHL_V22_FIT_RESOURCE_COST_BOUNDARY"}),
        "ledger_calculation_present": ledger_has(candidate / "data_sources" / "CALCULATIONS.csv", "calculation_id",
                                                  {"CALC_PHL_V22_FIT_RESIDUE_SUPPLY_COST"}),
        "ledger_maps_present": ledger_has(candidate / "data_sources" / "MODEL_MAP.csv", "map_id", {
            "MAP_PHL_V22_FIT_PHYSICAL_ACCOUNTING", "MAP_PHL_V22_FIT_RENEWABLE_MEMBERSHIP",
            "MAP_PHL_V22_FIT_POSTSOLVE_CASHFLOW"}),
        "ledger_gap_present": ledger_has(candidate / "data_sources" / "GAPS.csv", "item", {"FIT incidence and financing"}),
        "ledger_change_present": ledger_has(candidate / "data_sources" / "CHANGES.csv", "change_id",
                                             {"CHG_PHL_V22_FIT_ACCOUNTING_R9_20260820"}),
    })

    failures = [name for name, passed in checks.items() if not passed]
    report = {
        "schema": "philippines-v22-fit-accounting-r9-deterministic-gate-v1",
        "status": "passed" if not failures else "failed",
        "control": str(control), "candidate": str(candidate),
        "changed_json_files": sorted(changed), "checks": checks, "failures": failures,
        "optimizer_runs": 0,
        "promotion_allowed": False,
        "promotion_rule": "BASE first; only if optimal run COAL_PHASEOUT, RE and EV concurrently; promote only if all four are optimal from the exact candidate source.",
    }
    output = candidate / "documentation" / "fit_accounting_r9_deterministic_gate.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
