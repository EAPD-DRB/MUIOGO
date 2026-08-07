#!/usr/bin/env python3
"""Apply the non-forcing Philippines v16 water-demand calibration.

The generator copies the source JSON into a disposable MUIO data store,
passes the two new groundwater-electricity links through UpdateCase, and then
overlays only the approved source parameters:

* gross crop-irrigation IAR = inherited net IAR / 0.38;
* public-water AAD = PSA Scenario 2 population * 70 L/person/day;
* public-water OAR = 0.75 (25% NRW); and
* groundwater pumping electricity IAR = 0.70 PJ/km3.

It deliberately adds no irrigated-area commodity, demand, activity bound,
share, or user-defined constraint. Irrigated area remains endogenous.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import types
from copy import deepcopy
from decimal import Decimal, getcontext
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE_STORAGE = REPO / "WebAPP" / "DataStorage"
SOURCE_CASE_ENTRY = SOURCE_STORAGE / "Philippines_v16"
SOURCE_CASE = SOURCE_CASE_ENTRY.resolve()

BASE_SCENARIO = "SC_0"
IRRIGATION_WATER = "COM_sp9qb"  # AGRWATPHL
PUBLIC_WATER = "COM_n1j3l"  # PHL_PUB_WAT
PUBLIC_GWT = "TEC_5edgp"  # PHL_DEM_PUB_GWT_WAT
PUBLIC_SUR = "TEC_24bf8"  # PHL_DEM_PUB_SUR_WAT
POWER_GWT = "TEC_goiza"  # PHL_DEM_PWR_GWT_WAT
SERVICES_ELECTRICITY = "COM_opmhk"  # PHL_SER_ELE
POWER_ELECTRICITY = "COM_o7vja"  # PHL_POW_ELE

IRRIGATION_EFFICIENCY = Decimal("0.38")
PER_CAPITA_LITRES_PER_DAY = Decimal("70")
PUBLIC_OAR = Decimal("0.75")
PUMPING_ELECTRICITY_PJ_PER_KM3 = Decimal("0.70")

POPULATION_THOUSAND = {
    2020: Decimal("109202.72"),
    2025: Decimal("113863.08"),
    2030: Decimal("118873.79"),
    2035: Decimal("123963.52"),
    2040: Decimal("128826.05"),
    2045: Decimal("133024.51"),
    2050: Decimal("136298.85"),
    2055: Decimal("138672.75"),
}

GLOBAL_FILES = ("Parameters.json", "Variables.json", "Duals.json", "Indicators.json")
PROMOTED_FILES = ("genData.json", "RYTCM.json", "RYC.json")


dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(REPO / "API"))

from Classes.Base import Config  # noqa: E402
from Classes.Case.UpdateCaseClass import UpdateCase  # noqa: E402


getcontext().prec = 40


def read_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".codex-tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def semantic_source_snapshot(case_path: Path) -> dict[str, object]:
    return {path.name: read_json(path) for path in sorted(case_path.glob("*.json"))}


def keyed_rows(parameter: dict, scenario: str) -> dict[tuple, dict]:
    return {
        tuple(row.get(name) for name in ("TechId", "CommId", "MoId")): row
        for row in parameter[scenario]
    }


def population_for_year(year: int) -> Decimal:
    if year in POPULATION_THOUSAND:
        return POPULATION_THOUSAND[year]
    lower = max(anchor for anchor in POPULATION_THOUSAND if anchor < year)
    upper = min(anchor for anchor in POPULATION_THOUSAND if anchor > year)
    fraction = Decimal(year - lower) / Decimal(upper - lower)
    return POPULATION_THOUSAND[lower] + fraction * (
        POPULATION_THOUSAND[upper] - POPULATION_THOUSAND[lower]
    )


def public_demand_km3(year: int) -> float:
    # population is in thousand persons; 1 km3 = 1e12 litres.
    value = (
        population_for_year(year)
        * Decimal("1000")
        * PER_CAPITA_LITRES_PER_DAY
        * Decimal("365")
        / Decimal("1e12")
    )
    return float(value)


def prepare_disposable_target(target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"refusing to replace target: {target}")
    if target.resolve() == SOURCE_CASE:
        raise ValueError("disposable target resolves to the live source case")

    target.parent.mkdir(parents=True, exist_ok=True)
    for name in GLOBAL_FILES:
        destination = target.parent / name
        if not destination.exists():
            shutil.copy2(SOURCE_STORAGE / name, destination)

    target.mkdir()
    for source in sorted(SOURCE_CASE.glob("*.json")):
        shutil.copy2(source, target / source.name)

    (target / "view").mkdir()
    shutil.copy2(SOURCE_CASE / "view" / "resData.json", target / "view" / "resData.json")
    for run in read_json(target / "view" / "resData.json")["osy-cases"]:
        (target / "res" / run["Case"] / "csv").mkdir(parents=True)


def add_groundwater_electricity_links(gen: dict) -> None:
    technologies = {item["TechId"]: item for item in gen["osy-tech"]}
    additions = {
        PUBLIC_GWT: SERVICES_ELECTRICITY,
        POWER_GWT: POWER_ELECTRICITY,
    }
    for tech_id, commodity_id in additions.items():
        technology = technologies[tech_id]
        if commodity_id in technology["IAR"]:
            raise AssertionError(f"electricity link already exists for {technology['Tech']}")
        technology["IAR"].append(commodity_id)


def apply_parameter_overlays(
    target: Path,
    source_ratio: dict,
    source_demand: dict,
    gen: dict,
) -> dict:
    years = [str(year) for year in gen["osy-years"]]
    irrigation_techs = {
        item["TechId"] for item in gen["osy-tech"] if item["Tech"].startswith("LNDAGRPHLC")
    }
    if len(irrigation_techs) != 8:
        raise AssertionError(f"expected 8 LNDAGRPHLC technologies, found {len(irrigation_techs)}")

    ratio = read_json(target / "RYTCM.json")
    base_iar = keyed_rows(ratio["IAR"], BASE_SCENARIO)
    source_base_iar = keyed_rows(source_ratio["IAR"], BASE_SCENARIO)
    base_oar = keyed_rows(ratio["OAR"], BASE_SCENARIO)

    gross_rows = 0
    gross_positive_rows = 0
    for key, source_row in source_base_iar.items():
        tech_id, commodity_id, _mode = key
        if tech_id not in irrigation_techs or commodity_id != IRRIGATION_WATER:
            continue
        gross_rows += 1
        target_row = base_iar[key]
        positive = False
        for year in years:
            value = source_row[year]
            if value is None:
                raise AssertionError(f"base irrigation IAR is null: {key} {year}")
            if value == 0:
                target_row[year] = 0
            else:
                positive = True
                target_row[year] = float(Decimal(str(value)) / IRRIGATION_EFFICIENCY)
        gross_positive_rows += int(positive)

    if gross_rows != 240 or gross_positive_rows != 95:
        raise AssertionError(
            f"unexpected irrigation IAR coverage: {gross_rows} rows, "
            f"{gross_positive_rows} positive rows"
        )

    for tech_id in (PUBLIC_GWT, PUBLIC_SUR):
        row = base_oar[(tech_id, PUBLIC_WATER, 1)]
        for year in years:
            row[year] = float(PUBLIC_OAR)

    pumping_links = {
        (PUBLIC_GWT, SERVICES_ELECTRICITY, 1),
        (POWER_GWT, POWER_ELECTRICITY, 1),
    }
    for key in pumping_links:
        row = base_iar[key]
        for year in years:
            row[year] = float(PUMPING_ELECTRICITY_PJ_PER_KM3)

    write_json(target / "RYTCM.json", ratio)

    demand = read_json(target / "RYC.json")
    public_rows = [
        row for row in demand["AAD"][BASE_SCENARIO] if row["CommId"] == PUBLIC_WATER
    ]
    if len(public_rows) != 1:
        raise AssertionError(f"expected one base PHL_PUB_WAT AAD row, found {len(public_rows)}")
    public_row = public_rows[0]
    for year in years:
        public_row[year] = public_demand_km3(int(year))
    write_json(target / "RYC.json", demand)

    return {
        "years": years,
        "irrigation_rows": gross_rows,
        "positive_irrigation_rows": gross_positive_rows,
        "public_demand_2020_km3": public_row["2020"],
        "public_demand_2030_km3": public_row["2030"],
        "public_demand_2050_km3": public_row["2050"],
        "public_demand_2053_km3": public_row["2053"],
    }


def validate_allowlisted_diff(
    before: dict[str, object],
    target: Path,
    expected_gen: dict,
    summary: dict,
) -> None:
    after = semantic_source_snapshot(target)
    changed = {name for name in before if before[name] != after[name]}
    if changed != set(PROMOTED_FILES):
        raise AssertionError(f"unexpected semantic source changes: {sorted(changed)}")
    if read_json(target / "genData.json") != expected_gen:
        raise AssertionError("genData diff exceeds the two approved electricity links")

    source_ratio = before["RYTCM.json"]
    ratio = after["RYTCM.json"]
    source_demand = before["RYC.json"]
    demand = after["RYC.json"]
    years = summary["years"]

    irrigation_techs = {
        item["TechId"]
        for item in expected_gen["osy-tech"]
        if item["Tech"].startswith("LNDAGRPHLC")
    }
    new_keys = {
        (PUBLIC_GWT, SERVICES_ELECTRICITY, mode) for mode in range(1, 31)
    } | {
        (POWER_GWT, POWER_ELECTRICITY, mode) for mode in range(1, 31)
    }

    for scenario in source_ratio["IAR"]:
        old_rows = keyed_rows(source_ratio["IAR"], scenario)
        new_rows = keyed_rows(ratio["IAR"], scenario)
        if set(new_rows) - set(old_rows) != new_keys:
            raise AssertionError(f"unexpected new IAR rows in {scenario}")
        for key, old_row in old_rows.items():
            new_row = new_rows[key]
            is_gross_irrigation = (
                scenario == BASE_SCENARIO
                and key[0] in irrigation_techs
                and key[1] == IRRIGATION_WATER
            )
            if is_gross_irrigation:
                for year in years:
                    old = old_row[year]
                    expected = 0 if old == 0 else float(Decimal(str(old)) / IRRIGATION_EFFICIENCY)
                    if new_row[year] != expected:
                        raise AssertionError(f"wrong gross irrigation IAR: {key} {year}")
            elif new_row != old_row:
                raise AssertionError(f"unapproved existing IAR change: {scenario} {key}")

        for key in new_keys:
            row = new_rows[key]
            for year in years:
                if scenario == BASE_SCENARIO:
                    expected = (
                        float(PUMPING_ELECTRICITY_PJ_PER_KM3) if key[2] == 1 else 0
                    )
                else:
                    expected = None
                if row[year] != expected:
                    raise AssertionError(f"wrong pumping IAR: {scenario} {key} {year}")

    for scenario in source_ratio["OAR"]:
        old_rows = keyed_rows(source_ratio["OAR"], scenario)
        new_rows = keyed_rows(ratio["OAR"], scenario)
        if set(old_rows) != set(new_rows):
            raise AssertionError(f"OAR structure changed in {scenario}")
        for key, old_row in old_rows.items():
            approved = scenario == BASE_SCENARIO and key in {
                (PUBLIC_GWT, PUBLIC_WATER, 1),
                (PUBLIC_SUR, PUBLIC_WATER, 1),
            }
            if approved:
                if any(new_rows[key][year] != float(PUBLIC_OAR) for year in years):
                    raise AssertionError(f"wrong public-water OAR: {key}")
            elif new_rows[key] != old_row:
                raise AssertionError(f"unapproved OAR change: {scenario} {key}")

    for parameter_id, scenarios in source_demand.items():
        for scenario, old_rows in scenarios.items():
            new_rows = demand[parameter_id][scenario]
            if len(old_rows) != len(new_rows):
                raise AssertionError(f"demand row count changed: {parameter_id} {scenario}")
            for old_row, new_row in zip(old_rows, new_rows, strict=True):
                approved = (
                    parameter_id == "AAD"
                    and scenario == BASE_SCENARIO
                    and old_row.get("CommId") == PUBLIC_WATER
                )
                if approved:
                    for year in years:
                        if new_row[year] != public_demand_km3(int(year)):
                            raise AssertionError(f"wrong public demand in {year}")
                elif new_row != old_row:
                    raise AssertionError(
                        f"unapproved commodity change: {parameter_id} {scenario}"
                    )

    gen = after["genData.json"]
    if any(item.get("Comm") == "PHL_IRR_AREA" for item in gen["osy-comm"]):
        raise AssertionError("forbidden irrigated-area commodity was added")
    if any("IRR" in item.get("Con", "") and "AREA" in item.get("Con", "") for item in gen["osy-constraints"]):
        raise AssertionError("forbidden irrigated-area constraint was added")


def build_candidate(target: Path) -> dict:
    prepare_disposable_target(target)
    before = semantic_source_snapshot(target)
    source_hashes = {name: sha256(SOURCE_CASE / name) for name in PROMOTED_FILES}

    gen = deepcopy(before["genData.json"])
    add_groundwater_electricity_links(gen)
    write_json(target / "genData.json", gen)

    Config.DATA_STORAGE = target.parent
    UpdateCase(target.name, gen).updateCase()

    summary = apply_parameter_overlays(
        target,
        source_ratio=before["RYTCM.json"],
        source_demand=before["RYC.json"],
        gen=gen,
    )
    validate_allowlisted_diff(before, target, gen, summary)

    manifest = {
        "source_case": str(SOURCE_CASE),
        "target_case": str(target),
        "source_hashes": source_hashes,
        "candidate_hashes": {name: sha256(target / name) for name in PROMOTED_FILES},
        "calibration": {
            "irrigation_efficiency": float(IRRIGATION_EFFICIENCY),
            "public_litres_per_person_day": float(PER_CAPITA_LITRES_PER_DAY),
            "public_output_ratio": float(PUBLIC_OAR),
            "non_revenue_water_fraction": float(Decimal("1") - PUBLIC_OAR),
            "groundwater_pumping_pj_per_km3": float(PUMPING_ELECTRICITY_PJ_PER_KM3),
            **{key: value for key, value in summary.items() if key != "years"},
        },
        "non_forcing_assertions": {
            "irrigated_area_is_endogenous": True,
            "irrigated_area_commodity_added": False,
            "irrigated_area_constraint_added": False,
            "technology_activity_bounds_added": False,
        },
    }
    write_json(target / "water_demand_calibration_manifest.json", manifest)
    return manifest


def promote_candidate(target: Path, backup: Path) -> dict:
    manifest = read_json(target / "water_demand_calibration_manifest.json")
    if backup.exists():
        raise FileExistsError(f"refusing to replace backup: {backup}")
    backup.mkdir(parents=True)

    for name in PROMOTED_FILES:
        live_hash = sha256(SOURCE_CASE / name)
        if live_hash != manifest["source_hashes"][name]:
            raise AssertionError(f"live source changed since candidate creation: {name}")
        if sha256(target / name) != manifest["candidate_hashes"][name]:
            raise AssertionError(f"candidate changed since validation: {name}")
        shutil.copy2(SOURCE_CASE / name, backup / name)

    for name in PROMOTED_FILES:
        temporary = SOURCE_CASE / f".{name}.water-demand-candidate"
        shutil.copy2(target / name, temporary)
        temporary.replace(SOURCE_CASE / name)

    promoted_hashes = {name: sha256(SOURCE_CASE / name) for name in PROMOTED_FILES}
    if promoted_hashes != manifest["candidate_hashes"]:
        raise AssertionError("promoted hashes do not match validated candidate")

    report = {
        "source_case": str(SOURCE_CASE),
        "candidate_case": str(target),
        "backup": str(backup),
        "promoted_hashes": promoted_hashes,
    }
    write_json(backup / "promotion_report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()

    target = args.target.resolve()
    if args.promote:
        if args.backup is None:
            parser.error("--backup is required with --promote")
        result = promote_candidate(target, args.backup.resolve())
    else:
        result = build_candidate(target)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
