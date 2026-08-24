#!/usr/bin/env python3
"""Build a disposable Philippines v23 Package 1 source candidate.

The script does not generate solver data or optimize. Structural edits pass
through UpdateCase; all permanent model values remain in source JSON files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
SOURCE = STORAGE / "Philippines_v22"
LEDGER_SOURCE = STORAGE / ".Philippines_v22-ev-truck-turnover-candidate-20260824" / "data_sources"
DEFAULT_TARGET = STORAGE / ".Philippines_v23-package1-candidate-20260824"
API = ROOT / "API"
if str(API) not in sys.path:
    sys.path.insert(0, str(API))

BASE = "SC_0"
YEARS = tuple(str(y) for y in range(2020, 2054))
BIOFUEL_IMPORT_ID = "TEC_v23bioimp"
BIOFUEL_IMPORT_NAME = "PHL_PRO_IMP_BIOF"
RESERVE_CONSTRAINT_ID = "CO_v23reserve"
RESERVE_CONSTRAINT_NAME = "PHL_POW_RESERVE_MARGIN"

PEAK_TO_AVERAGE = 15282 / (101756 * 1000 / 8760)
RESERVE_MULTIPLIER = 1.25
RESERVE_ACTIVITY_COEFFICIENT = PEAK_TO_AVERAGE * RESERVE_MULTIPLIER / 31.536
TD_INPUT_PER_OUTPUT = (83243 + 9742) / 83243
BIOFUEL_IMPORT_COST = 24.5

PRE2026_BUILD_GW = {
    "PHL_POW_PP_WON": 1.5,
    "PHL_POW_PP_WOF": 0.0,
    "PHL_POW_PP_SPV": 4.0,
    "PHL_POW_PP_COAL": 2.0,
    "PHL_POW_PP_COAL_CCS": 0.0,
    "PHL_POW_PP_NGCC": 2.0,
    "PHL_POW_PP_NGCC_CCS": 0.0,
    "PHL_POW_GEO_OLD": 0.15,
    "PHL_POW_PP_HY_LA": 1.0,
    "PHL_POW_PP_H2": 0.0,
    "PHL_POW_PP_BIOM_CCS": 0.0,
    "PHL_POW_PP_NUSMR": 0.0,
    "PHL_POW_PP_NU": 0.0,
    "PHL_POW_TD": 4.0,
}

NEW_THERMAL_AF = {
    "PHL_POW_PP_COAL": 0.85,
    "PHL_POW_PP_COAL_CCS": 0.83,
    "PHL_POW_PP_NGCC": 0.90,
    "PHL_POW_PP_NGCC_CCS": 0.88,
    "PHL_POW_PP_NU": 0.90,
    "PHL_POW_PP_NUSMR": 0.90,
    "PHL_POW_PP_H2": 0.90,
    "PHL_POW_PP_BIOM_CCS": 0.80,
}

CAPACITY_CREDIT = {
    "PHL_POW_CHP_COAL_OLD": 0.9361653523880883,
    "PHL_POW_CHP_NG_OLD": 0.9518030412744388,
    "PHL_POW_CHP_OIL_OLD": 0.7207666525043667,
    "PHL_POW_CHP_BIOM_OLD": 0.6379079123826553,
    "PHL_POW_CHP_BIOM_FIT_OLD": 0.6379079123826553,
    "PHL_POW_PP_COAL": 0.85,
    "PHL_POW_PP_COAL_CCS": 0.83,
    "PHL_POW_PP_NGCC": 0.90,
    "PHL_POW_PP_NGCC_CCS": 0.88,
    "PHL_POW_PP_NU": 0.90,
    "PHL_POW_PP_NUSMR": 0.90,
    "PHL_POW_PP_H2": 0.90,
    "PHL_POW_PP_BIOM_CCS": 0.80,
    "PHL_POW_GEO_OLD": 0.70,
    "PHL_POW_PP_HY_LA": 0.80,
}

FULL_HORIZON_CLOSED = (
    "PHL_POW_GH2_COAL",
    "PHL_AGR_HEAT_COAL",
    "PHL_HOU_COOK_COAL",
)

GAL_MWH_TO_KM3_PJ = 3.785411784e-12 / 3.6e-6
COOLING_GAL_MWH = {
    "PHL_POW_CHP_COAL_OLD": 36350,
    "PHL_POW_CHP_NG_OLD": 11380,
    "PHL_POW_CHP_OIL_OLD": 35000,
    "PHL_POW_CHP_BIOM_OLD": 35000,
    "PHL_POW_CHP_BIOM_FIT_OLD": 35000,
    "PHL_POW_PP_COAL": 1005,
    "PHL_POW_PP_COAL_CCS": 1277,
    "PHL_POW_PP_NGCC": 253,
    "PHL_POW_PP_NGCC_CCS": 496,
    "PHL_POW_PP_NU": 44350,
    "PHL_POW_PP_NUSMR": 1101,
    "PHL_POW_PP_BIOM_CCS": 1200,
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tech_maps(gen):
    return ({row["Tech"]: row["TechId"] for row in gen["osy-tech"]},
            {row["TechId"]: row for row in gen["osy-tech"]})


def comm_maps(gen):
    return ({row["Comm"]: row["CommId"] for row in gen["osy-comm"]},
            {row["CommId"]: row for row in gen["osy-comm"]})


def rows_for(table, parameter, tech_id, **coordinates):
    return [
        row for row in table[parameter][BASE]
        if row.get("TechId") == tech_id
        and all(row.get(key) == value for key, value in coordinates.items())
    ]


def one_row(table, parameter, tech_id, **coordinates):
    rows = rows_for(table, parameter, tech_id, **coordinates)
    if len(rows) != 1:
        raise AssertionError((parameter, tech_id, coordinates, len(rows)))
    return rows[0]


def inherit_coordinate(table, parameter, coordinate, fields, years=YEARS):
    for scenario, rows in table[parameter].items():
        if scenario == BASE:
            continue
        for row in rows:
            if all(row.get(field) == value for field, value in zip(fields, coordinate)):
                for year in years:
                    row[year] = None


def mutate_structure(gen):
    tech_id, by_id = tech_maps(gen)
    comm_id, _ = comm_maps(gen)
    if BIOFUEL_IMPORT_NAME in tech_id:
        raise AssertionError("biofuel import technology already exists")
    gen["osy-tech"].append({
        "TechId": BIOFUEL_IMPORT_ID,
        "Tech": BIOFUEL_IMPORT_NAME,
        "Desc": "Positive-cost biofuel import boundary; replaces the undefined input-free domestic processor.",
        "CapUnitId": "PJ",
        "ActUnitId": "PJ",
        "TG": [],
        "IAR": [],
        "OAR": [comm_id["PHL_PRO_BIOF"]],
        "INCR": [], "ITCR": [], "EAR": [],
    })

    charcoal = by_id[tech_id["PHL_HOU_COOK_COAL"]]
    charcoal["IAR"] = [comm_id["PHL_PRO_BIOM"]]
    charcoal["Desc"] = (
        "Closed household charcoal-stove proxy using biomass-energy input; "
        "existing stock retires and no new stock may enter."
    )

    ccs = sorted(
        row["Tech"] for row in gen["osy-tech"]
        if "_CCS" in row["Tech"] and row["Tech"] != BIOFUEL_IMPORT_NAME
    )
    members = [tech_id[name] for name in CAPACITY_CREDIT] + [tech_id["PHL_POW_TD"]]
    if any(row.get("ConId") == RESERVE_CONSTRAINT_ID for row in gen["osy-constraints"]):
        raise AssertionError("reserve constraint already exists")
    gen["osy-constraints"].append({
        "ConId": RESERVE_CONSTRAINT_ID,
        "Con": RESERVE_CONSTRAINT_NAME,
        "Desc": (
            "DOE 25% planning reserve: credited grid generation capacity must cover "
            "the endogenous annual grid throughput converted at the observed peak-to-average ratio."
        ),
        "Tag": 0,
        "CM": members,
    })
    gen["osy-casename"] = "Philippines_v23"
    gen["osy-date"] = "2026-08-24"
    gen["osy-desc"] = (
        "Philippines v23 Package 1 physical-possibility and adequacy repair. "
        "Undefined biofuel processing is disabled behind a positive-cost import boundary; "
        "the inherited household coal label becomes a closed biomass-energy charcoal proxy; "
        "technology entry, build, availability, cooling, T&D, solar timing, worst-day electricity "
        "profiles and reserve accounting are corrected without activity or share targets.\n\n"
        + gen["osy-desc"]
    )
    return ccs


def set_base_series(table, parameter, tech_id, values, *, coordinate_fields=("TechId",), coordinates=()):
    row = one_row(table, parameter, tech_id, **dict(zip(coordinate_fields[1:], coordinates)))
    for year, value in values.items():
        row[year] = value
    inherit_coordinate(
        table, parameter, (tech_id, *coordinates), coordinate_fields,
        years=tuple(values),
    )


def overlay_parameters(target: Path, ccs_technologies: list[str]):
    gen = read_json(target / "genData.json")
    tech_id, _ = tech_maps(gen)
    comm_id, _ = comm_maps(gen)

    ryt = read_json(target / "RYT.json")
    for name, ceiling in PRE2026_BUILD_GW.items():
        set_base_series(
            ryt, "TAMaxCI", tech_id[name],
            {"2020": 0.0, **{str(y): ceiling for y in range(2021, 2026)}},
        )
    for name in FULL_HORIZON_CLOSED:
        set_base_series(ryt, "TAMaxCI", tech_id[name], {year: 0.0 for year in YEARS})
    set_base_series(ryt, "TAMaxCI", tech_id["PHL_PRO_PROC_BIOF"], {year: 0.0 for year in YEARS})
    set_base_series(ryt, "TAU", tech_id["PHL_PRO_PROC_BIOF"], {year: 0.0 for year in YEARS})
    for name in ccs_technologies:
        set_base_series(
            ryt, "TAMaxCI", tech_id[name],
            {str(y): 0.0 for y in range(2020, 2030)},
        )
    for name, value in NEW_THERMAL_AF.items():
        set_base_series(ryt, "AF", tech_id[name], {year: value for year in YEARS})
    set_base_series(ryt, "RC", BIOFUEL_IMPORT_ID, {year: 0.0 for year in YEARS})
    set_base_series(ryt, "TAMaxCI", BIOFUEL_IMPORT_ID, {year: 999999.0 for year in YEARS})
    set_base_series(ryt, "TAU", BIOFUEL_IMPORT_ID, {year: 999999.0 for year in YEARS})
    set_base_series(ryt, "AF", BIOFUEL_IMPORT_ID, {year: 1.0 for year in YEARS})
    write_json(target / "RYT.json", ryt)

    rt = read_json(target / "RT.json")
    for scenario, rows in rt["CAU"].items():
        rows[0][BIOFUEL_IMPORT_ID] = 1.0 if scenario == BASE else None
    for scenario, rows in rt["OL"].items():
        rows[0][BIOFUEL_IMPORT_ID] = 1 if scenario == BASE else None
    write_json(target / "RT.json", rt)

    rytm = read_json(target / "RYTM.json")
    for row in rows_for(rytm, "VC", BIOFUEL_IMPORT_ID):
        for year in YEARS:
            row[year] = BIOFUEL_IMPORT_COST if row["MoId"] == 1 else 0.0
    for scenario, rows in rytm["VC"].items():
        if scenario != BASE:
            for row in rows:
                if row["TechId"] == BIOFUEL_IMPORT_ID:
                    for year in YEARS:
                        row[year] = None
    write_json(target / "RYTM.json", rytm)

    rytcm = read_json(target / "RYTCM.json")
    # UpdateCase created the new/replaced structural coordinates; give only
    # mode 1 a physical coefficient and leave all global spare modes at zero.
    affected_iar = set()
    for row in rows_for(
        rytcm, "IAR", tech_id["PHL_HOU_COOK_COAL"], CommId=comm_id["PHL_PRO_BIOM"]
    ):
        for year in YEARS:
            row[year] = 5.0 if row["MoId"] == 1 else 0.0
        affected_iar.add((row["TechId"], row["CommId"]))
    td_coordinate = (tech_id["PHL_POW_TD"], comm_id["PHL_POW_ELE"])
    for row in rows_for(rytcm, "IAR", *td_coordinate[:1], CommId=td_coordinate[1]):
        for year in YEARS:
            row[year] = TD_INPUT_PER_OUTPUT if row["MoId"] == 1 else 0.0
        affected_iar.add(td_coordinate)
    water = comm_id["PHL_PWR_WAT"]
    for name, gallons in COOLING_GAL_MWH.items():
        coordinate = (tech_id[name], water)
        rows = rows_for(rytcm, "IAR", coordinate[0], CommId=coordinate[1])
        if not rows:
            raise AssertionError(f"missing cooling-water coordinate for {name}")
        for row in rows:
            for year in YEARS:
                row[year] = gallons * GAL_MWH_TO_KM3_PJ if row["MoId"] == 1 else 0.0
        affected_iar.add(coordinate)
    for scenario, rows in rytcm["IAR"].items():
        if scenario != BASE:
            for row in rows:
                if (row["TechId"], row["CommId"]) in affected_iar:
                    for year in YEARS:
                        row[year] = None
    for row in rows_for(rytcm, "OAR", BIOFUEL_IMPORT_ID, CommId=comm_id["PHL_PRO_BIOF"]):
        for year in YEARS:
            row[year] = 1.0 if row["MoId"] == 1 else 0.0
    for scenario, rows in rytcm["OAR"].items():
        if scenario != BASE:
            for row in rows:
                if row["TechId"] == BIOFUEL_IMPORT_ID:
                    for year in YEARS:
                        row[year] = None
    write_json(target / "RYTCM.json", rytcm)

    rytts = read_json(target / "RYTTs.json")
    # Correct the retained UTC-indexed six-bracket solar trace to UTC+8 by a
    # two-bracket rotation within each ordinary season. Worst-day solar stays 0.
    solar_rows = {
        row["TsId"]: row for row in rytts["CF"][BASE]
        if row["TechId"] == tech_id["PHL_POW_PP_SPV"]
    }
    ordinary_seasons = [row["SeId"] for row in gen["osy-se"] if row["SeId"] != "SE_ugd96"]
    for season in ordinary_seasons:
        block = [
            row["TsId"] for row in sorted(gen["osy-ts"], key=lambda item: int(item["Ts"]))
            if row["SE"] == season
        ]
        if len(block) != 6:
            raise AssertionError((season, block))
        for year in YEARS:
            old = [solar_rows[ts][year] for ts in block]
            rotated = [old[4], old[5], old[0], old[1], old[2], old[3]]
            for ts, value in zip(block, rotated):
                solar_rows[ts][year] = value
    for row in rows_for(rytts, "CF", BIOFUEL_IMPORT_ID):
        for year in YEARS:
            row[year] = 1.0
    affected_cf = {tech_id["PHL_POW_PP_SPV"], BIOFUEL_IMPORT_ID}
    for scenario, rows in rytts["CF"].items():
        if scenario != BASE:
            for row in rows:
                if row["TechId"] in affected_cf:
                    for year in YEARS:
                        row[year] = None
    write_json(target / "RYTTs.json", rytts)

    # Place the observed national grid peak only on fixed electricity final
    # demands. Fuel-neutral agriculture services retain their service profile.
    rycts = read_json(target / "RYCTs.json")
    ryts = read_json(target / "RYTs.json")
    ys = {row["TsId"]: row for row in ryts["YS"][BASE]}
    worst = [
        row["TsId"] for row in sorted(gen["osy-ts"], key=lambda item: int(item["Ts"]))
        if row["SE"] == "SE_ugd96"
    ]
    peak_ts = worst[4]
    profile_ids = {comm_id["PHL_HOU_ELEF"], comm_id["PHL_SER_ELEF"]}
    by_comm = {}
    for row in rycts["SDP"][BASE]:
        by_comm.setdefault(row["CommId"], {})[row["TsId"]] = row
    for commodity in profile_ids:
        rows = by_comm[commodity]
        for year in YEARS:
            old_peak = float(rows[peak_ts][year])
            new_peak = PEAK_TO_AVERAGE * float(ys[peak_ts][year])
            old_total = sum(float(rows[ts][year]) for ts in by_comm[commodity])
            # Move the peak increment out of the other worst-day slices and
            # close the inherited 0.999999999 display-rounding gap to 1.0.
            adjustment = new_peak - old_peak + old_total - 1.0
            donor = sum(float(rows[ts][year]) for ts in worst if ts != peak_ts)
            for ts in worst:
                rows[ts][year] = (
                    new_peak if ts == peak_ts
                    else float(rows[ts][year]) - adjustment * float(rows[ts][year]) / donor
                )
    for scenario, rows in rycts["SDP"].items():
        if scenario != BASE:
            for row in rows:
                if row["CommId"] in profile_ids:
                    for year in YEARS:
                        row[year] = None
    write_json(target / "RYCTs.json", rycts)

    rycn = read_json(target / "RYCn.json")
    reserve_rows = [
        row for row in rycn["UCC"][BASE]
        if row["ConId"] == RESERVE_CONSTRAINT_ID
    ]
    if len(reserve_rows) != 1:
        raise AssertionError(("UCC", RESERVE_CONSTRAINT_ID, len(reserve_rows)))
    reserve_constant = reserve_rows[0]
    for year in YEARS:
        reserve_constant[year] = 0.0
    inherit_coordinate(rycn, "UCC", (RESERVE_CONSTRAINT_ID,), ("ConId",))
    write_json(target / "RYCn.json", rycn)

    rytcn = read_json(target / "RYTCn.json")
    reserve_members = {*CAPACITY_CREDIT, "PHL_POW_TD"}
    for name in reserve_members:
        tid = tech_id[name]
        values = {
            "CCM": -CAPACITY_CREDIT.get(name, 0.0),
            "CNCM": 0.0,
            "CAM": RESERVE_ACTIVITY_COEFFICIENT if name == "PHL_POW_TD" else 0.0,
        }
        for parameter, value in values.items():
            row = one_row(rytcn, parameter, tid, ConId=RESERVE_CONSTRAINT_ID)
            for year in YEARS:
                row[year] = value
            inherit_coordinate(
                rytcn, parameter, (tid, RESERVE_CONSTRAINT_ID), ("TechId", "ConId")
            )
    write_json(target / "RYTCn.json", rytcn)


def append_csv(path: Path, rows: list[dict]) -> None:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        existing = list(reader)
    key = fields[0]
    seen = {row[key] for row in existing}
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        for row in rows:
            if row[key] not in seen:
                writer.writerow({field: row.get(field, "") for field in fields})


def write_ledger(target: Path, ccs_technologies: list[str], source_hashes: dict[str, str]):
    ledger = target / "data_sources"
    if ledger.exists():
        shutil.rmtree(ledger)
    shutil.copytree(LEDGER_SOURCE, ledger)
    snapshot = ledger / "snapshots" / "philippines_v23_package1_sources_2026-08-24.json"
    facts = {
        "schema": "philippines-v23-package1-source-extract-v1",
        "access_date": "2026-08-24",
        "source_case": str(SOURCE),
        "source_hashes": source_hashes,
        "classifications": {
            "DOE peak, sales, losses and dependable capacities": "physical drivers",
            "DOE 25 percent reserve": "continuing planning constraint",
            "existing cooking and power stocks": "initial stocks",
            "future technology activity and shares": "endogenous; benchmark only",
        },
        "facts": {
            "peak_mw": 15282,
            "consumption_gwh": 101756,
            "sales_gwh": 83243,
            "system_losses_gwh": 9742,
            "reserve_multiplier": RESERVE_MULTIPLIER,
            "peak_to_average": PEAK_TO_AVERAGE,
            "td_input_per_output": TD_INPUT_PER_OUTPUT,
            "reserve_activity_coefficient": RESERVE_ACTIVITY_COEFFICIENT,
            "cooling_gal_per_mwh": COOLING_GAL_MWH,
            "new_thermal_availability": NEW_THERMAL_AF,
            "pre2026_build_gw_per_year": PRE2026_BUILD_GW,
            "ccs_first_build_year": 2030,
            "biofuel_import_cost_musd_per_pj": BIOFUEL_IMPORT_COST,
        },
        "sources": {
            "DOE_PEP_2020_2040": {
                "url": "https://doe.gov.ph/sites/default/files/pdf/pep/PEP-2020-2040-Final%20eCopy-as-of-15-June-2023.pdf",
                "locator": "power planning reserve; hydrogen roadmap; biofuel roadmap",
            },
            "DOE_POWER_2020": {
                "url": "https://doe.gov.ph/site/epimb/articles/group/reports?category=Power+Situation+Report",
                "locator": "2020 Power Situation Report and power statistics",
            },
            "DOE_PEP_2023_2050_VOL2": {
                "url": "https://legacy.doe.gov.ph/sites/default/files/pdf/pep/PEP%202023-2050%20Vol.%20II.pdf",
                "locator": "Hydrogen and derivatives roadmap, Figure 16 and surrounding text",
            },
            "NREL_50900": {
                "url": "https://www.nrel.gov/docs/fy11osti/50900.pdf",
                "locator": "Table 3 withdrawal medians",
            },
            "IRENA_BIOENERGY_2022": {
                "url": "https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2022/Aug/IRENA_Bioenergy_for_the_transition_2022.pdf",
                "locator": "transport biofuel wholesale cost ranges",
            },
        },
    }
    write_json(snapshot, facts)
    digest = sha256(snapshot)
    local = str(snapshot.relative_to(ledger))

    source_rows = []
    for sid, provider, product, variable, url in [
        ("SRC_PHL_V23_PARENT", "MUIOGO", "Philippines_v22 August 24 canonical source", "parent source identity", ""),
        ("SRC_PHL_V23_DOE_PEP", "Philippine Department of Energy", "Philippine Energy Plan 2020-2040", "reserve, hydrogen and biofuel planning", facts["sources"]["DOE_PEP_2020_2040"]["url"]),
        ("SRC_PHL_V23_DOE_POWER", "Philippine Department of Energy", "2020 Power Situation Report and statistics", "peak, demand, sales, losses and dependable capacity", facts["sources"]["DOE_POWER_2020"]["url"]),
        ("SRC_PHL_V23_DOE_PEP_2023", "Philippine Department of Energy", "Philippine Energy Plan 2023-2050 Volume II", "hydrogen policy/R&D status", facts["sources"]["DOE_PEP_2023_2050_VOL2"]["url"]),
        ("SRC_PHL_V23_NREL_WATER", "National Renewable Energy Laboratory", "Operational Water Consumption and Withdrawal Factors", "cooling withdrawal factors", facts["sources"]["NREL_50900"]["url"]),
        ("SRC_PHL_V23_IRENA_BIOFUEL", "IRENA", "Bioenergy for the Energy Transition", "biofuel border-price proxy", facts["sources"]["IRENA_BIOENERGY_2022"]["url"]),
    ]:
        source_rows.append({
            "source_id": sid, "provider": provider, "product": product,
            "edition": "retained 2026-08-24", "reference_period": "2020-2053",
            "geography": "Philippines", "variable": variable, "source_unit": "source-specific",
            "exact_locator": "See retained hashed extract", "url": url,
            "access_date": "2026-08-24", "license": "Provider terms",
            "sha256": digest, "local_file": local,
            "notes": "Numerical facts, model classifications and source locators retained locally.",
        })
    append_csv(ledger / "SOURCES.csv", source_rows)

    assumptions = [
        {"assumption_id": "ASM_PHL_V23_NON_FORCING", "statement": "No generation, activity, build, dispatch or market share is fixed; observations classify stocks, demands, continuing physical constraints or benchmarks.", "evidence_source_ids": "SRC_PHL_V23_PARENT", "rationale": "Repository master rule."},
        {"assumption_id": "ASM_PHL_V23_BIOFUEL_BORDER", "statement": "Disable the undefined no-input domestic processor and permit positive-cost biofuel imports at the model border.", "central_value": BIOFUEL_IMPORT_COST, "unit": "MUSD/PJ", "evidence_source_ids": "SRC_PHL_V23_IRENA_BIOFUEL;SRC_PHL_V23_PARENT", "rationale": "An explicitly named import is a physical model boundary; an input-free domestic conversion is not."},
        {"assumption_id": "ASM_PHL_V23_CHARCOAL_PROXY", "statement": "The coal-labelled household stove is a closed initial-stock charcoal proxy consuming biomass-energy rather than fossil coal.", "evidence_source_ids": "SRC_PHL_V23_PARENT", "rationale": "Preserve the calibrated initial stock while removing fossil-coal replenishment and new entry."},
        {"assumption_id": "ASM_PHL_V23_CCS_2030", "statement": "No modeled CCS technology may add capacity before 2030.", "central_value": 2030, "unit": "first build year", "evidence_source_ids": "SRC_PHL_V23_DOE_PEP;SRC_PHL_V23_DOE_PEP_2023", "rationale": "The Philippine plans describe policy/R&D and future deployment, not commercial Philippine CCS capacity in the historical interval."},
        {"assumption_id": "ASM_PHL_V23_COAL_H2_CLOSED", "statement": "Coal hydrogen and new coal agriculture heat are unavailable over the horizon.", "evidence_source_ids": "SRC_PHL_V23_DOE_PEP;SRC_PHL_V23_DOE_PEP_2023", "rationale": "DOE treats hydrogen as R&D/policy development and the PEP states benefits are subject to non-fossil feedstock; no continuing Philippine coal-hydrogen or new coal-heat route is evidenced."},
        {"assumption_id": "ASM_PHL_V23_THERMAL_AF", "statement": "New thermal technologies use disclosed planning availability below one; DOE dependable/nameplate ratios remain on existing fleets.", "central_value": json.dumps(NEW_THERMAL_AF, sort_keys=True), "unit": "fraction", "evidence_source_ids": "SRC_PHL_V23_DOE_POWER", "rationale": "Perfect annual availability is physically impossible; values are transparent planning assumptions, not utilization targets."},
        {"assumption_id": "ASM_PHL_V23_PRE2026_BUILD", "statement": "The 2026-2029 physical delivery envelopes are extended back to 2021-2025; technologies without an eligible near-term route remain at zero.", "central_value": json.dumps(PRE2026_BUILD_GW, sort_keys=True), "unit": "GW/year", "evidence_source_ids": "SRC_PHL_V23_PARENT", "rationale": "Remove the historical 999999 construction hole without imposing a project or minimum build."},
        {"assumption_id": "ASM_PHL_V23_RESERVE_CREDIT", "statement": "Firm-capacity credits use DOE legacy dependable ratios and disclosed new-technology planning availability; variable renewables receive no annual firm credit in this conservative reserve screen.", "central_value": json.dumps(CAPACITY_CREDIT, sort_keys=True), "unit": "fraction", "evidence_source_ids": "SRC_PHL_V23_DOE_POWER;SRC_PHL_V23_DOE_PEP", "rationale": "Separate reserve accounting from physical timeslice capacity factors."},
    ]
    append_csv(ledger / "ASSUMPTIONS.csv", assumptions)

    calculations = [
        {"calculation_id": "CALC_PHL_V23_TD", "formula": "(sales + system losses) / sales", "source_ids": "SRC_PHL_V23_DOE_POWER", "input_values": "83243;9742", "input_units": "GWh;GWh", "output_value": TD_INPUT_PER_OUTPUT, "output_unit": "PJ/PJ", "script_path": "scripts/build_philippines_v23_package1.py", "script_version": "v1"},
        {"calculation_id": "CALC_PHL_V23_PEAK", "formula": "peak MW / (annual consumption GWh * 1000 / 8760)", "source_ids": "SRC_PHL_V23_DOE_POWER", "input_values": "15282;101756", "input_units": "MW;GWh", "output_value": PEAK_TO_AVERAGE, "output_unit": "ratio", "script_path": "scripts/build_philippines_v23_package1.py", "script_version": "v1"},
        {"calculation_id": "CALC_PHL_V23_RESERVE", "formula": "peak_to_average * 1.25 / 31.536", "source_ids": "SRC_PHL_V23_DOE_POWER;SRC_PHL_V23_DOE_PEP", "assumption_ids": "ASM_PHL_V23_RESERVE_CREDIT", "input_values": f"{PEAK_TO_AVERAGE};1.25;31.536", "input_units": "ratio;ratio;PJ/GW-year", "output_value": RESERVE_ACTIVITY_COEFFICIENT, "output_unit": "GW/(PJ/year)", "script_path": "scripts/build_philippines_v23_package1.py", "script_version": "v1"},
        {"calculation_id": "CALC_PHL_V23_COOLING", "formula": "gal/MWh * 3.785411784e-12 km3/gal / 3.6e-6 PJ/MWh", "source_ids": "SRC_PHL_V23_NREL_WATER", "input_values": json.dumps(COOLING_GAL_MWH, sort_keys=True), "input_units": "gal/MWh", "output_value": json.dumps({k: v * GAL_MWH_TO_KM3_PJ for k, v in COOLING_GAL_MWH.items()}, sort_keys=True), "output_unit": "km3/PJ", "script_path": "scripts/build_philippines_v23_package1.py", "script_version": "v1"},
    ]
    append_csv(ledger / "CALCULATIONS.csv", calculations)

    maps = [
        {"map_id": "MAP_PHL_V23_BIOFUEL", "model_file": "genData.json;RYT.json;RYTM.json;RYTCM.json", "parameter": "route;TAMaxCI;TAU;VC;OAR", "entity": f"PHL_PRO_PROC_BIOF;{BIOFUEL_IMPORT_NAME}", "mode": "1", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "undefined processor disabled; import OAR=1 and VC=24.5", "model_unit": "mixed", "evidence_ids": "ASM_PHL_V23_BIOFUEL_BORDER", "evidence_type": "physical boundary and sourced cost proxy"},
        {"map_id": "MAP_PHL_V23_CHARCOAL", "model_file": "genData.json;RYT.json;RYTCM.json", "parameter": "IAR membership;TAMaxCI;IAR", "entity": "PHL_HOU_COOK_COAL", "mode": "1", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "input=PHL_PRO_BIOM; TAMaxCI=0; IAR=5", "model_unit": "PJ/PJ", "evidence_ids": "ASM_PHL_V23_CHARCOAL_PROXY", "evidence_type": "initial-stock physical proxy"},
        {"map_id": "MAP_PHL_V23_ELIGIBILITY", "model_file": "RYT.json", "parameter": "TAMaxCI", "entity": ";".join(ccs_technologies + ["PHL_POW_GH2_COAL", "PHL_AGR_HEAT_COAL"]), "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "CCS=0 through 2029; coal hydrogen and coal agriculture heat=0 full horizon", "model_unit": "capacity/year", "evidence_ids": "ASM_PHL_V23_CCS_2030;ASM_PHL_V23_COAL_H2_CLOSED", "evidence_type": "technology eligibility"},
        {"map_id": "MAP_PHL_V23_TD", "model_file": "RYTCM.json", "parameter": "IAR", "entity": "PHL_POW_TD", "mode": "1", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "CALC_PHL_V23_TD", "model_unit": "PJ/PJ", "evidence_ids": "CALC_PHL_V23_TD", "evidence_type": "derived physical parameter"},
        {"map_id": "MAP_PHL_V23_SOLAR", "model_file": "RYTTs.json", "parameter": "CF", "entity": "PHL_POW_PP_SPV", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "ordinary six-bracket seasons rotated +8 hours; worst day remains zero", "model_unit": "fraction", "evidence_ids": "SRC_PHL_V23_PARENT", "evidence_type": "timezone correction"},
        {"map_id": "MAP_PHL_V23_COOLING", "model_file": "RYTCM.json", "parameter": "IAR", "entity": ";".join(COOLING_GAL_MWH), "mode": "1", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "CALC_PHL_V23_COOLING", "model_unit": "km3/PJ", "evidence_ids": "CALC_PHL_V23_COOLING", "evidence_type": "derived; mapping limitation disclosed"},
        {"map_id": "MAP_PHL_V23_BUILD", "model_file": "RYT.json", "parameter": "TAMaxCI", "entity": ";".join(PRE2026_BUILD_GW), "scenario": "SC_0 with inheritance", "years": "2020-2025", "value_or_expression": json.dumps(PRE2026_BUILD_GW, sort_keys=True), "model_unit": "GW/year", "evidence_ids": "ASM_PHL_V23_PRE2026_BUILD", "evidence_type": "continuing physical upper envelope"},
        {"map_id": "MAP_PHL_V23_AF", "model_file": "RYT.json", "parameter": "AF", "entity": ";".join(NEW_THERMAL_AF), "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": json.dumps(NEW_THERMAL_AF, sort_keys=True), "model_unit": "fraction", "evidence_ids": "ASM_PHL_V23_THERMAL_AF", "evidence_type": "planning assumption"},
        {"map_id": "MAP_PHL_V23_WORST_DAY", "model_file": "RYCTs.json", "parameter": "SDP", "entity": "PHL_HOU_ELEF;PHL_SER_ELEF", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": f"peak SDP/YearSplit={PEAK_TO_AVERAGE}; annual sum=1", "model_unit": "fraction", "evidence_ids": "CALC_PHL_V23_PEAK", "evidence_type": "derived fixed-electricity profile"},
        {"map_id": "MAP_PHL_V23_RESERVE", "model_file": "genData.json;RYCn.json;RYTCn.json", "parameter": "UDC;UCC;CCM;CAM", "entity": RESERVE_CONSTRAINT_NAME, "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "-sum(capacity_credit*TotalCapacity)+CALC_PHL_V23_RESERVE*TotalAnnualActivity(PHL_POW_TD)<=0", "model_unit": "GW", "evidence_ids": "CALC_PHL_V23_RESERVE;ASM_PHL_V23_RESERVE_CREDIT", "evidence_type": "continuing physical planning constraint"},
    ]
    append_csv(ledger / "MODEL_MAP.csv", maps)
    append_csv(ledger / "GAPS.csv", [
        {"item": "Plant-level cooling-system/source mapping", "why_absent": "The national model has fuel/technology aggregates but no condenser type, cooling loop or intake source by plant.", "upgrade_source": "Plant-level cooling technology, withdrawal, consumption and freshwater/seawater intake register.", "priority": "high", "notes": "NREL withdrawal medians correct the scale; the technology mapping remains conservative and disclosed."},
        {"item": "Technology-specific forced-outage and capacity-credit series", "why_absent": "DOE publishes dependable/nameplate values for the legacy aggregate fleets, not every prospective technology over 2020-2053.", "upgrade_source": "Philippine plant-class outage histories and accredited capacity by reserve product.", "priority": "high", "notes": "New thermal AF/credit values are transparent planning assumptions; no dispatch is fitted."},
        {"item": "Domestic biofuel feedstock chain", "why_absent": "A reconciled crop, residue, land, conversion-yield and trade balance is not available in the case.", "upgrade_source": "Separate ethanol/biodiesel feedstock, conversion, import and blend commodities with land/resource reconciliation.", "priority": "high", "notes": "V23 disables the undefined domestic processor and uses a positive-cost border import instead."},
        {"item": "Charcoal production and trade chain", "why_absent": "The model lacks kiln yields, wood source, charcoal prices and trade statistics.", "upgrade_source": "Add explicit wood-to-charcoal conversion, sustainable feedstock, price and trade objects.", "priority": "high", "notes": "V23 retains only the closed initial stove stock as a biomass-energy proxy."},
        {"item": "Storage and network deliverability in reserve accounting", "why_absent": "The national copperplate has no zonal transmission topology and the reserve UDC uses annual grid throughput.", "upgrade_source": "Grid peak by region, interconnector transfer limits, reserve accreditation, outage distributions and storage capacity credit.", "priority": "high", "notes": "The timeslice balance still enforces energy adequacy; the reserve UDC adds a conservative firm-capacity planning margin."},
    ])
    append_csv(ledger / "CHANGES.csv", [{
        "change_id": "CHG_PHL_V23_PACKAGE1_20260824", "date": str(date(2026, 8, 24)),
        "class": "B", "description": "Package 1 physical-possibility, timing and adequacy repair on the latest validated v22 parent.",
        "model_objects": "genData.json;RT.json;RYT.json;RYTM.json;RYTCM.json;RYTTs.json;RYCTs.json;RYCn.json;RYTCn.json",
        "evidence_path": "calculation_notes/MODEL_FIXES_PACKAGE_1_V23_2026-08-24.md",
        "map_rows_affected": ";".join(row["map_id"] for row in maps),
        "resolve_status": "candidate_pending_deterministic_gate_generation_matrix_and_one_BASE_solve",
        "author": "Codex", "commit": "",
        "notes": "No endogenous activity/share/dispatch/build target; generic source gate must pass before generation or optimization.",
    }])

    notes = ledger / "calculation_notes" / "MODEL_FIXES_PACKAGE_1_V23_2026-08-24.md"
    notes.write_text("""# Philippines v23 Package 1 — candidate design

This candidate starts from the latest validated Philippines v22 source, including the August 24 EV/truck turnover correction. Observations are classified as initial stocks, exogenous final demands, continuing physical/planning constraints, or validation benchmarks. No activity, generation, dispatch, technology share, realized investment, or fuel share is forced.

The undefined input-free domestic biofuel processor is disabled. A separate positive-cost import technology supplies the existing biofuel commodity at the model border. The household coal-labelled stove is rewired to biomass energy, retained only as a closed charcoal initial-stock proxy, and receives no new capacity. Coal hydrogen and new coal agriculture heat are closed; CCS entry begins no earlier than 2030.

The main T&D input ratio uses DOE sales plus system losses over sales. Solar CFs are shifted from UTC to Philippine local time without changing annual energy. The DOE peak-to-average profile is applied only to fixed household and service electricity demands; fuel-neutral agriculture motive-power and processing services retain their service profiles. New thermal AFs are below one. Historical 2021-2025 unlimited power/T&D build cells are replaced by finite delivery envelopes.

Reserve is not hidden in CF. One user-defined inequality requires credited firm generation capacity to cover endogenous annual `PHL_POW_TD` activity at the DOE peak-to-average ratio plus 25 percent planning reserve. Because the RHS-equivalent term uses endogenous grid throughput, future electrification raises the requirement automatically.

Qualification order is mandatory: generic source-only physical gate; Package 1 exact-cell and semantic validation; UI-path generation and preprocessing; `glpsol --check`; one disposable BASE CBC solve; result comparison with the retained v22 canonical baseline; then source-only promotion and byte-identity checks. Policy scenarios are not optimizer prerequisites for this source-only physical package unless BASE or scenario inheritance diagnostics show a material unresolved issue.
""", encoding="utf-8")
    return snapshot, digest


def build(target: Path):
    from Classes.Case.UpdateCaseClass import UpdateCase
    from Classes.Base import Config

    if target.exists():
        raise FileExistsError(target)
    if not SOURCE.is_dir() or not LEDGER_SOURCE.is_dir():
        raise FileNotFoundError("parent case or authoritative cumulative ledger is missing")
    source_hashes = {path.name: sha256(path) for path in SOURCE.glob("*.json")}
    shutil.copytree(
        SOURCE, target,
        ignore=shutil.ignore_patterns("res", "data_sources", ".DS_Store"),
    )
    gen = read_json(target / "genData.json")
    ccs_technologies = mutate_structure(gen)
    Config.DATA_STORAGE = STORAGE
    UpdateCase(target.name, gen).updateCase()
    write_json(target / "genData.json", gen)
    overlay_parameters(target, ccs_technologies)
    snapshot, digest = write_ledger(target, ccs_technologies, source_hashes)
    manifest = {
        "schema": "philippines-v23-package1-build-v1",
        "parent_case": str(SOURCE),
        "parent_canonical_result": str(STORAGE / ".Philippines_v22-ev-truck-turnover-candidate-20260824"),
        "candidate_case": str(target),
        "source_hashes": source_hashes,
        "candidate_hashes": {path.name: sha256(path) for path in target.glob("*.json")},
        "changed_source_files": sorted(
            path.name for path in target.glob("*.json")
            if source_hashes.get(path.name) != sha256(path)
        ),
        "ccs_technologies": ccs_technologies,
        "ledger_snapshot": str(snapshot),
        "ledger_snapshot_sha256": digest,
        "optimizer_runs": 0,
        "model_generation_runs": 0,
        "required_next_step": "Run generic source gate and exact Package 1 validator before generation.",
    }
    write_json(target / "documentation" / "package1_v23_build_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()
    build(args.target.resolve())


if __name__ == "__main__":
    main()
