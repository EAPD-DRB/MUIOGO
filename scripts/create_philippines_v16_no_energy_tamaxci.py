#!/usr/bin/env python3
"""Build a disposable Philippines v16 case with no energy-sector TAMaxCI.

The generator copies the live Philippines v16 source JSON into a disposable
MUIO data store and resets every base-scenario
``TotalAnnualMaxCapacityInvestment`` (TAMaxCI) row that belongs to the energy
sector to the parameter default, which is the effectively unbounded 999999.
Nothing else changes, so the resulting LP is the BASE run with the
new-capacity upper bounds on energy technologies removed.

Energy sector here means the technologies whose capacity and activity units
are energy units, that is the PHL_PRO_ supply chain, PHL_POW_ power block,
PHL_INDU_/PHL_SER_/PHL_HOU_/PHL_TRA_ end-use devices, the PHL_AGR_ energy
devices, and the PHL_FSH_ energy devices. The land block (LND*, MINLNDTOT,
ENV_LAND), the water block (MINPRCPHL, PHL_WTR_*, PHL_DEM_*_WAT,
DEMAGR*PHL, ENV_WATER) and the crop-area accounting technologies are left
untouched. In particular the ENV_LAND and ENV_WATER accounting terminals keep
their TAMaxCI of 0, because ENV_LAND is pinned by the Tag-1 BAL_ENV_LAND
constraint.

Only the base scenario SC_0 is rewritten. The COAL_PHASEOUT and RE scenarios
keep their own scenario-defining TAMaxCI overrides, since they do not enter
the BASE run.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import types
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE_STORAGE = REPO / "WebAPP" / "DataStorage"
SOURCE_CASE_ENTRY = SOURCE_STORAGE / "Philippines_v16"
SOURCE_CASE = SOURCE_CASE_ENTRY.resolve()

BASE_SCENARIO = "SC_0"
PARAMETER = "TAMaxCI"
PARAMETER_GROUP = "RYT"

ENERGY_PREFIXES = (
    "PHL_PRO_",
    "PHL_POW_",
    "PHL_INDU_",
    "PHL_SER_",
    "PHL_HOU_",
    "PHL_TRA_",
    "PHL_AGR_",
    "PHL_FSH_",
)
# PHL_DEM_* are the four water withdrawal pass-throughs, not energy devices.
NON_ENERGY_PREFIXES = ("PHL_DEM_",)

GLOBAL_FILES = ("Parameters.json", "Variables.json", "Duals.json", "Indicators.json")


dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(REPO / "API"))


def read_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n")
    temporary.replace(path)


def parameter_default(name: str) -> float:
    parameters = read_json(SOURCE_STORAGE / "Parameters.json")
    for item in parameters[PARAMETER_GROUP]:
        if item["id"] == name:
            return item["default"]
    raise KeyError(f"{name} is not defined in Parameters.json group {PARAMETER_GROUP}")


def is_energy(tech_name: str) -> bool:
    if tech_name.startswith(NON_ENERGY_PREFIXES):
        return False
    return tech_name.startswith(ENERGY_PREFIXES)


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


def clear_energy_bounds(target: Path) -> dict:
    gen = read_json(target / "genData.json")
    names = {item["TechId"]: item["Tech"] for item in gen["osy-tech"]}
    years = [str(year) for year in gen["osy-years"]]
    default = parameter_default(PARAMETER)

    bounds = read_json(target / "RYT.json")
    rows = bounds[PARAMETER][BASE_SCENARIO]

    cleared: list[dict] = []
    retained: list[dict] = []
    for row in rows:
        name = names[row["TechId"]]
        before = [row.get(year) for year in years]
        binding = [value for value in before if value is not None and value != default]
        if not binding:
            continue
        record = {
            "tech": name,
            "tech_id": row["TechId"],
            "min": min(binding),
            "max": max(binding),
            "distinct": len(set(binding)),
            "years_bounded": len(binding),
            "value_2020": before[0],
            "value_2030": before[years.index("2030")],
            "value_2053": before[-1],
        }
        if is_energy(name):
            for year in years:
                row[year] = default
            cleared.append(record)
        else:
            retained.append(record)

    write_json(target / "RYT.json", bounds)

    # Re-read and assert the rewrite is complete for the energy sector.
    verify = read_json(target / "RYT.json")[PARAMETER][BASE_SCENARIO]
    for row in verify:
        name = names[row["TechId"]]
        if not is_energy(name):
            continue
        offending = [
            (year, row.get(year))
            for year in years
            if row.get(year) is not None and row.get(year) != default
        ]
        if offending:
            raise AssertionError(f"{name} still bounded: {offending[:3]}")

    return {
        "parameter": PARAMETER,
        "scenario": BASE_SCENARIO,
        "default": default,
        "cleared_count": len(cleared),
        "retained_count": len(retained),
        "cleared": sorted(cleared, key=lambda item: item["tech"]),
        "retained": sorted(retained, key=lambda item: item["tech"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        type=Path,
        default=SOURCE_STORAGE / ".Philippines_v16-no-energy-tamaxci",
        help="disposable case directory to create",
    )
    args = parser.parse_args()

    target = args.target.absolute()
    prepare_disposable_target(target)
    manifest = clear_energy_bounds(target)
    manifest["source_case"] = str(SOURCE_CASE)
    manifest["target_case"] = str(target)

    write_json(target / "no_energy_tamaxci_manifest.json", manifest)
    print(
        json.dumps(
            {
                key: manifest[key]
                for key in (
                    "parameter",
                    "scenario",
                    "default",
                    "cleared_count",
                    "retained_count",
                    "target_case",
                )
            },
            indent=2,
        )
    )
    print("retained (non-energy):", [item["tech"] for item in manifest["retained"]])


if __name__ == "__main__":
    main()
