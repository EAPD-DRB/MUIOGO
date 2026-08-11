#!/usr/bin/env python3
"""Build a data-only Philippines v16 achieved-crop-yield candidate.

The calibration replaces inherited absolute GAEZ potential yields with
unit-matched 2020 achieved national yields.  It changes no technology,
commodity, mode, demand, activity bound, share, or user constraint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from decimal import Decimal, getcontext
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STORAGE = REPO / "WebAPP" / "DataStorage"
SOURCE_CASE = (STORAGE / "Philippines_v16").resolve()
INPUTS = REPO / "scripts" / "data" / "philippines_v16_crop_yields.json"
BASE_SCENARIO = "SC_0"
GLOBAL_FILES = ("Parameters.json", "Variables.json", "Duals.json", "Indicators.json")
SOURCE_FILES = ("genData.json", "RYT.json", "RYTCM.json", "RYTM.json")
CLUSTER_TECHS = (
    "TEC_ibnh8", "TEC_9lvqs", "TEC_3mwof", "TEC_ckkki",
    "TEC_1ky0a", "TEC_oeqz2", "TEC_72dqm", "TEC_xaiae",
)
RICE_HIGH_RAINFED = "TEC_gnski"
RICE_HIGH_IRRIGATED = "TEC_dyiju"
PHP_PER_USD_2021 = Decimal("49.25")
RICE_COST_PHP_PER_KG = {
    "rice_rainfed": Decimal("13.95"),
    "rice_irrigated": Decimal("12.49"),
}

getcontext().prec = 40


def read_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def keyed_rows(parameter: dict, keys: tuple[str, ...]) -> dict[tuple, dict]:
    return {tuple(row.get(key) for key in keys): row for row in parameter[BASE_SCENARIO]}


def prepare_target(target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"refusing to replace target: {target}")
    if target.resolve() == SOURCE_CASE:
        raise ValueError("target resolves to the live case")
    for name in GLOBAL_FILES:
        destination = target.parent / name
        if not destination.exists():
            shutil.copy2(STORAGE / name, destination)
    target.mkdir(parents=True)
    for source in sorted(SOURCE_CASE.glob("*.json")):
        shutil.copy2(source, target / source.name)
    (target / "view").mkdir()
    shutil.copy2(SOURCE_CASE / "view" / "resData.json", target / "view" / "resData.json")


def snapshot(case: Path) -> dict[str, object]:
    return {path.name: read_json(path) for path in sorted(case.glob("*.json"))}


def achieved_oar(observation: dict) -> Decimal:
    production_t = Decimal(str(observation["production_t"]))
    area_ha = Decimal(str(observation["area_ha"]))
    return production_t / area_ha / Decimal("10")


def update_descriptions(gen: dict) -> int:
    replacements = {
        "Vegetables (tomato gaez proxy) land option": "Other vegetables, fresh n.e.c. aggregate land option",
        "Land allocated to vegetables (tomato GAEZ proxy)": "Land allocated to other vegetables, fresh n.e.c.",
        "Vegetable production represented by the GAEZ tomato proxy.": "Other vegetables, fresh n.e.c. aggregate production.",
        "Sugar-cane production.": "Fresh sugar-cane production.",
        "Coconut production.": "Coconut-with-husk production.",
        "Other crop production.": "Aggregate production of the five retained OTH crop components.",
    }
    changed = 0
    for collection in (gen["osy-tech"], gen["osy-comm"]):
        for item in collection:
            old = item.get("Desc", "")
            new = old
            for before, after in replacements.items():
                new = new.replace(before, after)
            if new != old:
                item["Desc"] = new
                changed += 1
    return changed


def build_candidate(target: Path) -> dict[str, object]:
    prepare_target(target)
    before = snapshot(target)
    inputs = read_json(INPUTS)
    observations = inputs["observations"]
    years = [str(year) for year in before["genData.json"]["osy-years"]]

    gen = read_json(target / "genData.json")
    commodity_ids = {item["Comm"]: item["CommId"] for item in gen["osy-comm"]}
    description_changes = update_descriptions(gen)
    write_json(target / "genData.json", gen)

    ryt = read_json(target / "RYT.json")
    rc = keyed_rows(ryt["RC"], ("TechId",))
    rainfed_capacity = Decimal(str(observations["rice_rainfed"]["area_ha"])) / Decimal("100000")
    irrigated_capacity = Decimal(str(observations["rice_irrigated"]["area_ha"])) / Decimal("100000")
    for year in years:
        rc[(RICE_HIGH_RAINFED,)][year] = float(rainfed_capacity)
        rc[(RICE_HIGH_IRRIGATED,)][year] = float(irrigated_capacity)
    write_json(target / "RYT.json", ryt)

    rytcm = read_json(target / "RYTCM.json")
    oar = keyed_rows(rytcm["OAR"], ("TechId", "CommId", "MoId"))
    oars: dict[str, Decimal] = {}
    row_changes = 0
    cell_changes = 0
    for name, observation in observations.items():
        value = achieved_oar(observation)
        oars[name] = value
        commodity = commodity_ids[observation["commodity"]]
        for tech_id in CLUSTER_TECHS:
            for mode in observation["modes"]:
                row = oar[(tech_id, commodity, mode)]
                changed_row = False
                for year in years:
                    if Decimal(str(row[year])) != value:
                        changed_row = True
                        cell_changes += 1
                    row[year] = float(value)
                row_changes += int(changed_row)
    write_json(target / "RYTCM.json", rytcm)

    # Rice variable cost is expressed per unit of land activity. Preserve the
    # sourced PHP/kg production cost after changing output per land activity.
    rytm = read_json(target / "RYTM.json")
    vc = keyed_rows(rytm["VC"], ("TechId", "MoId"))
    rice_vc_cells = 0
    for regime in ("rice_rainfed", "rice_irrigated"):
        per_mt = RICE_COST_PHP_PER_KG[regime] / PHP_PER_USD_2021 * Decimal("1000")
        value = oars[regime] * per_mt
        for tech_id in CLUSTER_TECHS:
            for mode in observations[regime]["modes"]:
                row = vc[(tech_id, mode)]
                for year in years:
                    if Decimal(str(row[year])) != value:
                        rice_vc_cells += 1
                    row[year] = float(value)
    write_json(target / "RYTM.json", rytm)

    after = snapshot(target)
    changed_files = sorted(name for name in before if before[name] != after[name])
    if changed_files != sorted(SOURCE_FILES):
        raise AssertionError(f"unexpected semantic source changes: {changed_files}")

    # Structural identity and non-forcing guards.
    for key in ("TechId", "Tech"):
        if [x[key] for x in before["genData.json"]["osy-tech"]] != [x[key] for x in after["genData.json"]["osy-tech"]]:
            raise AssertionError("technology structure changed")
    for key in ("CommId", "Comm"):
        if [x[key] for x in before["genData.json"]["osy-comm"]] != [x[key] for x in after["genData.json"]["osy-comm"]]:
            raise AssertionError("commodity structure changed")
    if before["genData.json"]["osy-constraints"] != after["genData.json"]["osy-constraints"]:
        raise AssertionError("user-defined constraints changed")
    for parameter in ("TAL", "TAU", "TAMinCI", "TAMinC", "TAMaxCI", "TAMaxC"):
        if before["RYT.json"][parameter] != after["RYT.json"][parameter]:
            raise AssertionError(f"activity/capacity bound changed: {parameter}")
    if before["RYTCM.json"]["IAR"] != after["RYTCM.json"]["IAR"]:
        raise AssertionError("water or other input ratios changed")
    for filename, parameter in (("RYT.json", "RC"), ("RYTCM.json", "OAR"), ("RYTM.json", "VC")):
        for scenario in before[filename][parameter]:
            if scenario != BASE_SCENARIO and before[filename][parameter][scenario] != after[filename][parameter][scenario]:
                raise AssertionError(f"policy scenario changed: {filename} {parameter} {scenario}")

    expected_area_mha = {
        name: float(Decimal(str(obs["area_ha"])) / Decimal("1000000"))
        for name, obs in observations.items()
    }
    manifest = {
        "schema": "philippines-v16-crop-yield-candidate-v1",
        "source_case": str(SOURCE_CASE),
        "target_case": str(target),
        "input_file": str(INPUTS),
        "input_sha256": sha256(INPUTS),
        "source_hashes": {name: sha256(SOURCE_CASE / name) for name in SOURCE_FILES},
        "candidate_hashes": {name: sha256(target / name) for name in SOURCE_FILES},
        "changed_source_files": changed_files,
        "description_records_changed": description_changes,
        "oar_rows_changed": row_changes,
        "oar_cells_changed": cell_changes,
        "rice_variable_cost_cells_changed": rice_vc_cells,
        "achieved_oar_mt_per_1000km2": {name: float(value) for name, value in oars.items()},
        "deterministic_2020_area_mha": expected_area_mha,
        "rice_capacity_1000km2": {
            "rainfed": float(rainfed_capacity),
            "irrigated": float(irrigated_capacity),
        },
        "classification": {
            "initial_stock": "2020 irrigated service area and rainfed rice area proxy",
            "final_demand": "unchanged existing crop-output demands",
            "continuing_constraint": "unchanged cluster land availability and water constraints",
            "benchmark_only": "observed crop areas; no activity target or share is added",
        },
        "non_forcing_assertions": {
            "technology_or_commodity_added": False,
            "demand_changed": False,
            "activity_or_share_bound_added": False,
            "udc_added": False,
            "absolute_gaez_potential_used_as_achieved_yield": False,
        },
    }
    write_json(target / "crop_yield_calibration_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, type=Path)
    args = parser.parse_args()
    build_candidate(args.target.resolve())


if __name__ == "__main__":
    main()
