#!/usr/bin/env python3
"""Build or promote the non-forcing Philippines v16 irrigated-rice calibration.

The calibration changes only observed initial stocks and the existing rice
production economics.  It does not add an irrigated-area demand, lower bound,
share, UDC, or activity pin.  Irrigated-land use remains an optimizer choice.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from decimal import Decimal, getcontext
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE_STORAGE = REPO / "WebAPP" / "DataStorage"
SOURCE_CASE = (SOURCE_STORAGE / "Philippines_v16").resolve()
BASE_SCENARIO = "SC_0"

PROMOTED_FILES = ("RT.json", "RYT.json", "RYTCM.json", "RYTM.json")
GLOBAL_FILES = ("Parameters.json", "Variables.json", "Duals.json", "Indicators.json")

# Existing model objects.
HIGH_RAINFED_OPTION = "TEC_gnski"   # LNDRCPHRTOT
HIGH_IRRIGATED_OPTION = "TEC_dyiju" # LNDRCPHITOT
LOW_RAINFED_OPTION = "TEC_2vnpr"    # LNDRCPLRTOT
LOW_IRRIGATED_OPTION = "TEC_3f392"  # LNDRCPLITOT
RICE_COMMODITY = "COM_zrfky"        # CRPRCP
RAINFED_MODES = (11, 14)
IRRIGATED_MODES = (17, 19)

# 2020 national observations.  One model land unit is 100,000 ha.
IRRIGATED_SERVICE_AREA_MHA = Decimal("2.006")
RAINFED_RICE_AREA_MHA = Decimal("1.47")
IRRIGATED_RICE_PRODUCTION_MT = Decimal("14.57")
RAINFED_RICE_PRODUCTION_MT = Decimal("4.72")

# 2021 national palay production costs and exchange rate.
IRRIGATED_COST_PHP_PER_KG = Decimal("12.49")
RAINFED_COST_PHP_PER_KG = Decimal("13.95")
PHP_PER_USD_2021 = Decimal("49.25")

# DA-PRDP indicative unit cost for an irrigation system.
NEW_IRRIGATION_PHP_PER_HA = Decimal("300000")
PHP_PER_USD_2020 = Decimal("49.62")
IRRIGATION_OPERATIONAL_LIFE_YEARS = 30

# Exogenous cluster land availability in RYT.TAU; used only to retain the
# inherited GAEZ spatial pattern while matching each national regime mean.
CLUSTER_TECHS = (
    "TEC_ibnh8", "TEC_9lvqs", "TEC_3mwof", "TEC_ckkki",
    "TEC_1ky0a", "TEC_oeqz2", "TEC_72dqm", "TEC_xaiae",
)

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


def semantic_snapshot(case: Path) -> dict[str, object]:
    return {path.name: read_json(path) for path in sorted(case.glob("*.json"))}


def keyed_rows(parameter: dict, scenario: str, keys: tuple[str, ...]) -> dict[tuple, dict]:
    return {tuple(row.get(key) for key in keys): row for row in parameter[scenario]}


def prepare_target(target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"refusing to replace target: {target}")
    if target.resolve() == SOURCE_CASE:
        raise ValueError("target resolves to the live case")
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


def national_target_oar(production_mt: Decimal, physical_area_mha: Decimal) -> Decimal:
    # Mt / Mha = t/ha.  Divide by 10 because one activity unit is 0.1 Mha.
    return production_mt / physical_area_mha / Decimal("10")


def apply_overlays(target: Path) -> dict[str, object]:
    rt = read_json(target / "RT.json")
    ryt = read_json(target / "RYT.json")
    rytcm = read_json(target / "RYTCM.json")
    rytm = read_json(target / "RYTM.json")
    gen = read_json(target / "genData.json")
    years = [str(year) for year in gen["osy-years"]]

    tech_names = {item["TechId"]: item["Tech"] for item in gen["osy-tech"]}
    crop_techs = {tech_id for tech_id in CLUSTER_TECHS}
    if any(not tech_names[tech_id].startswith("LNDAGRPHLC") for tech_id in crop_techs):
        raise AssertionError("cluster technology identity mismatch")

    # Initial physical stock: available capacity, never required activity.
    rc = keyed_rows(ryt["RC"], BASE_SCENARIO, ("TechId",))
    stock_units = {
        HIGH_IRRIGATED_OPTION: IRRIGATED_SERVICE_AREA_MHA * Decimal("10"),
        HIGH_RAINFED_OPTION: RAINFED_RICE_AREA_MHA * Decimal("10"),
    }
    for tech_id, value in stock_units.items():
        for year in years:
            rc[(tech_id,)][year] = float(value)

    # New irrigation expansion cost and asset life. Existing capacity is sunk RC.
    operational_life = rt["OL"][BASE_SCENARIO][0]
    for tech_id in (HIGH_IRRIGATED_OPTION, LOW_IRRIGATED_OPTION):
        operational_life[tech_id] = IRRIGATION_OPERATIONAL_LIFE_YEARS
    write_json(target / "RT.json", rt)

    cc = keyed_rows(ryt["CC"], BASE_SCENARIO, ("TechId",))
    irrigation_capital_cost = (
        NEW_IRRIGATION_PHP_PER_HA / PHP_PER_USD_2020
        * Decimal("100000") / Decimal("1000000")
    )
    for tech_id in (HIGH_IRRIGATED_OPTION, LOW_IRRIGATED_OPTION):
        for year in years:
            cc[(tech_id,)][year] = float(irrigation_capital_cost)
    write_json(target / "RYT.json", ryt)

    # Scale the inherited cluster pattern to observed annual output per unit of
    # physical land.  Irrigated annual productivity includes multiple cropping.
    tau = keyed_rows(ryt["TAU"], BASE_SCENARIO, ("TechId",))
    oar = keyed_rows(rytcm["OAR"], BASE_SCENARIO, ("TechId", "CommId", "MoId"))
    weights = {tech_id: Decimal(str(tau[(tech_id,)]["2020"])) for tech_id in CLUSTER_TECHS}
    weight_sum = sum(weights.values())

    high_mode_by_regime = {"rainfed": 11, "irrigated": 19}
    target_by_regime = {
        "rainfed": national_target_oar(RAINFED_RICE_PRODUCTION_MT, RAINFED_RICE_AREA_MHA),
        "irrigated": national_target_oar(IRRIGATED_RICE_PRODUCTION_MT, IRRIGATED_SERVICE_AREA_MHA),
    }
    scale_by_regime: dict[str, Decimal] = {}
    for regime, mode in high_mode_by_regime.items():
        inherited_mean = sum(
            weights[tech_id]
            * Decimal(str(oar[(tech_id, RICE_COMMODITY, mode)]["2020"]))
            for tech_id in CLUSTER_TECHS
        ) / weight_sum
        scale_by_regime[regime] = target_by_regime[regime] / inherited_mean

    rice_modes = {**{mode: "rainfed" for mode in RAINFED_MODES},
                  **{mode: "irrigated" for mode in IRRIGATED_MODES}}
    for tech_id in CLUSTER_TECHS:
        for mode, regime in rice_modes.items():
            row = oar[(tech_id, RICE_COMMODITY, mode)]
            factor = scale_by_regime[regime]
            for year in years:
                row[year] = float(Decimal(str(row[year])) * factor)
    write_json(target / "RYTCM.json", rytcm)

    # Full observed production cost per unit of crop activity.  This replaces
    # the inherited token 0.0001 cost but does not reward a particular area.
    cost_per_mt = {
        "rainfed": RAINFED_COST_PHP_PER_KG / PHP_PER_USD_2021 * Decimal("1000"),
        "irrigated": IRRIGATED_COST_PHP_PER_KG / PHP_PER_USD_2021 * Decimal("1000"),
    }
    vc = keyed_rows(rytm["VC"], BASE_SCENARIO, ("TechId", "MoId"))
    for tech_id in CLUSTER_TECHS:
        for mode, regime in rice_modes.items():
            vc_row = vc[(tech_id, mode)]
            crop_row = oar[(tech_id, RICE_COMMODITY, mode)]
            for year in years:
                vc_row[year] = float(Decimal(str(crop_row[year])) * cost_per_mt[regime])
    write_json(target / "RYTM.json", rytm)

    return {
        "years": years,
        "irrigated_stock_model_units": float(stock_units[HIGH_IRRIGATED_OPTION]),
        "irrigated_stock_mha": float(IRRIGATED_SERVICE_AREA_MHA),
        "rainfed_stock_model_units": float(stock_units[HIGH_RAINFED_OPTION]),
        "rainfed_stock_mha": float(RAINFED_RICE_AREA_MHA),
        "rainfed_target_oar": float(target_by_regime["rainfed"]),
        "irrigated_target_oar": float(target_by_regime["irrigated"]),
        "rainfed_yield_scale": float(scale_by_regime["rainfed"]),
        "irrigated_yield_scale": float(scale_by_regime["irrigated"]),
        "rainfed_cost_musd_per_mt": float(cost_per_mt["rainfed"]),
        "irrigated_cost_musd_per_mt": float(cost_per_mt["irrigated"]),
        "new_irrigation_capital_cost_musd_per_1000km2": float(irrigation_capital_cost),
        "new_irrigation_operational_life_years": IRRIGATION_OPERATIONAL_LIFE_YEARS,
    }


def validate_diff(before: dict[str, object], target: Path, summary: dict[str, object]) -> None:
    after = semantic_snapshot(target)
    changed = {name for name in before if before[name] != after[name]}
    if changed != set(PROMOTED_FILES):
        raise AssertionError(f"unexpected semantic source changes: {sorted(changed)}")
    if before["genData.json"] != after["genData.json"]:
        raise AssertionError("structural model changed")

    # Explicit master-rule guard: no activity bounds or UDC structure changed.
    for parameter in ("TAL", "TAU", "TAMinCI", "TAMinC", "TAMaxCI", "TAMaxC"):
        if before["RYT.json"][parameter] != after["RYT.json"][parameter]:
            raise AssertionError(f"forbidden activity/capacity bound change: {parameter}")
    if before["genData.json"].get("osy-constraints") != after["genData.json"].get("osy-constraints"):
        raise AssertionError("forbidden UDC change")

    # Policy scenarios remain null/inherited; only SC_0 is calibrated.
    for filename, parameters in {
        "RT.json": ("OL",),
        "RYT.json": ("RC", "CC"),
        "RYTCM.json": ("OAR",),
        "RYTM.json": ("VC",),
    }.items():
        for parameter in parameters:
            for scenario in before[filename][parameter]:
                if scenario != BASE_SCENARIO and (
                    before[filename][parameter][scenario] != after[filename][parameter][scenario]
                ):
                    raise AssertionError(f"policy row changed: {filename} {parameter} {scenario}")

    if summary["irrigated_stock_mha"] <= 0 or summary["rainfed_target_oar"] <= 0:
        raise AssertionError("non-positive calibration result")


def build_candidate(target: Path) -> dict[str, object]:
    prepare_target(target)
    before = semantic_snapshot(target)
    source_hashes = {name: sha256(SOURCE_CASE / name) for name in PROMOTED_FILES}
    summary = apply_overlays(target)
    validate_diff(before, target, summary)
    manifest = {
        "source_case": str(SOURCE_CASE),
        "target_case": str(target),
        "source_hashes": source_hashes,
        "candidate_hashes": {name: sha256(target / name) for name in PROMOTED_FILES},
        "calibration": summary,
        "physical_classification": {
            "initial_stock": "2020 irrigated service and rainfed rice land capacity",
            "final_demand": "unchanged food demand",
            "continuing_constraint": "none added",
            "benchmark_only": "observed irrigated use and the older approximately 1.7 Mha value",
        },
        "non_forcing_assertions": {
            "irrigated_area_activity_is_endogenous": True,
            "demand_added": False,
            "activity_or_share_bound_added": False,
            "udc_added": False,
            "food_demand_changed": False,
        },
    }
    write_json(target / "irrigated_rice_calibration_manifest.json", manifest)
    return manifest


def promote_candidate(target: Path, backup: Path) -> dict[str, object]:
    manifest = read_json(target / "irrigated_rice_calibration_manifest.json")
    if backup.exists():
        raise FileExistsError(f"refusing to replace backup: {backup}")
    backup.mkdir(parents=True)
    for name in PROMOTED_FILES:
        if sha256(SOURCE_CASE / name) != manifest["source_hashes"][name]:
            raise AssertionError(f"live source changed since candidate creation: {name}")
        if sha256(target / name) != manifest["candidate_hashes"][name]:
            raise AssertionError(f"candidate changed since creation: {name}")
        shutil.copy2(SOURCE_CASE / name, backup / name)
    for name in PROMOTED_FILES:
        temporary = SOURCE_CASE / f".{name}.irrigated-rice-candidate"
        shutil.copy2(target / name, temporary)
        temporary.replace(SOURCE_CASE / name)
    promoted_hashes = {name: sha256(SOURCE_CASE / name) for name in PROMOTED_FILES}
    if promoted_hashes != manifest["candidate_hashes"]:
        raise AssertionError("promoted hashes do not match the candidate")
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
