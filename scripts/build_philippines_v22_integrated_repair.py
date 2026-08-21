#!/usr/bin/env python3
"""Build the disposable Philippines v22 integrated physical-repair candidate.

The script never solves the model.  It copies Philippines_v21, passes structural
membership changes through UpdateCase, overlays sourced parameters, and writes
the six-table schema ledger.  The separate design gate must pass before model
generation, matrix creation, or optimization.
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
SOURCE = STORAGE / "Philippines_v21"
DEFAULT_TARGET = STORAGE / ".Philippines_v22-transition-scope-only-candidate-r8"
LEDGER_BASE = ROOT / "tmp" / "phl-v18-deployment-envelope-20260813" / "package" / "data_sources"
API = ROOT / "API"
if str(API) not in sys.path:
    sys.path.insert(0, str(API))

YEARS = tuple(str(year) for year in range(2020, 2054))
BASE = "SC_0"
CO2E = "EMI_0"
SCOPE_ONLY = True
PLANNING_RESERVE_FACTOR = 1.25
REPRESENTATIVE_DAYTYPE_ID = "DT_0"
REDUNDANT_DAYTYPE_ID = "DT_ii6mj"

# DOE PEP 2020-2040 Table 32, million litres/year.  The PEP uses 80% capacity
# utilization in its supply planning.  Linear interpolation is used between
# published milestones and the 2040 envelope is held constant thereafter.
BIOFUEL_CAPACITY_MLPY = {
    2020: (707.90, 380.50),
    2025: (1086.78, 944.15),
    2030: (1086.78, 1354.26),
    2035: (1331.93, 1913.05),
    2040: (1733.04, 2579.34),
}
BIODIESEL_MJ_PER_L = 33.3
BIOETHANOL_MJ_PER_L = 21.2
BIOFUEL_UTILIZATION = 0.80
BIOFUEL_COST_MUSD_PER_PJ = 24.5

# NREL/TP-6A20-50900 medians.  Conversion is
# gal/MWh * 3.785411784e-12 km3/gal / 3.6e-6 PJ/MWh.
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

# Planning availability assumptions for new physical thermal capacity.  Legacy
# fleet AFs already use DOE dependable/nameplate ratios and are not overwritten.
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

# Dependable-capacity factors applied through the existing worst-day capacity
# coefficients.  Variable renewables receive zero credit because the retained
# worst-day profiles are zero; the model may still use their energy normally.
CAPACITY_CREDIT = {
    "PHL_POW_CHP_COAL_OLD": 0.9361653523880883,
    "PHL_POW_CHP_NG_OLD": 0.9518030412744388,
    "PHL_POW_CHP_OIL_OLD": 0.7225874848938314,
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
    "PHL_POW_PP_SPV": 0.0,
    "PHL_POW_PP_WON": 0.0,
    "PHL_POW_PP_WOF": 0.0,
}

# The v18 envelopes are extended to the previously unconstrained historical
# interval.  Values are generous delivery ceilings, never minimum additions.
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
}

# No endogenous route is closed merely because its observed historical use is
# zero.  In particular, PHL_HOU_COOK_COAL is the documented charcoal proxy.
FULL_HORIZON_CLOSED = ()
# Technology activity dates remain endogenous.  Observed non-operation is a
# validation benchmark, not a reason to impose an arbitrary availability date.
CCS_BEFORE_2030_CLOSED = ()

# 2020 official inventory intensities divided by model physical land activity.
# Units are MtCO2e per 1000 km2-year of land-option activity.
RICE_CH4_FACTOR = 26.985 / 34.7144
MANAGED_SOIL_FACTOR = (6.875 + 2.277) / 119.9929
IRRIGATION_REQUIREMENT_BENCHMARK_KM3 = 33.28
GROUNDWATER_SHARE_BENCHMARK = 0.019
AGRICULTURE_GHGI_2020_MTCO2E = 54.080
MODELED_CROP_GHGI_2020_MTCO2E = 26.985 + 6.875 + 2.277

# Tier-1 screening carbon stocks, MtCO2 per 1000 km2.  Negative EACR means an
# increase in a land stock removes CO2 and a decrease releases it.  These are
# deliberately partial stock-change accounts and are disclosed as such.
LAND_STOCK_MT_PER_1000KM2 = {
    "LNDFORTOT": 52.0,
    "LNDGRSTOT": 2.0,
    "LNDOTHTOT": 1.0,
}
CROPLAND_STOCK_MT_PER_1000KM2 = 1.5

AFOLU_ACCOUNTING = {}

# World Bank/ESMAP typical end-use efficiencies.  The model's cooking demand is
# useful cooking energy, so IAR is fuel energy / useful energy.  This replaces
# the inherited physically impossible 100% efficiency without prescribing a
# fuel share or activity.
COOKING_EFFICIENCY = {
    "PHL_HOU_COOK_OIL": 0.60,   # LPG/kerosene aggregate; LPG-dominant in CPH
    "PHL_HOU_COOK_ELE": 0.70,
    "PHL_HOU_COOK_NG": 0.60,
    "PHL_HOU_COOK_COAL": 0.20,  # traditional charcoal proxy
    "PHL_HOU_COOK_BIOM": 0.15,  # traditional fuelwood/biomass
}

# Close the three free-energy agriculture-heat routes using the sector's
# existing 89%-efficient coal/biomass convention.  Electricity is direct
# resistive/process heat at unity input per useful output; this is an explicit
# judgement call, not a heat-pump assumption or an observed fuel-share target.
AGRICULTURE_HEAT_IAR = {
    "PHL_AGR_HEAT_OIL": ("PHL_PRO_OIL", 1.123595506),
    "PHL_AGR_HEAT_NG": ("PHL_PRO_NG", 1.123595506),
    "PHL_AGR_HEAT_ELE": ("PHL_AGR_ELE", 1.0),
}
AGRICULTURE_ENERGY_2024_PJ = 438.8 * 0.041868
AGRICULTURE_ELECTRICITY_SHARE_2024 = 0.656


def afolu_coefficients(crop_names: list[str]) -> dict[str, dict[str, float]]:
    return {
    }

# DOE 2020: 15,282 MW non-coincident peak and 101,756 GWh consumption.
PEAK_TO_AVERAGE = 15282 / (101756 * 1000 / 8760)
RESERVE_MULTIPLIER = 1.25
ADEQUACY_ACTIVITY_MULTIPLIER = PEAK_TO_AVERAGE * RESERVE_MULTIPLIER / 31.536

# DOE balance: 83,243 GWh sales and 9,742 GWh system losses.  Plant own-use is
# excluded from this pass-through ratio rather than being mislabeled T&D loss.
TD_INPUT_PER_OUTPUT = (83243 + 9742) / 83243


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
    return ({t["Tech"]: t["TechId"] for t in gen["osy-tech"]},
            {t["TechId"]: t for t in gen["osy-tech"]})


def comm_maps(gen):
    return ({c["Comm"]: c["CommId"] for c in gen["osy-comm"]},
            {c["CommId"]: c["Comm"] for c in gen["osy-comm"]})


def select_row(rows, tech_id, **keys):
    matches = [r for r in rows if r.get("TechId") == tech_id and all(r.get(k) == v for k, v in keys.items())]
    if len(matches) != 1:
        raise AssertionError((tech_id, keys, len(matches)))
    return matches[0]


def interpolate_milestones(year: int, index: int) -> float:
    if year >= 2040:
        return BIOFUEL_CAPACITY_MLPY[2040][index]
    anchors = sorted(BIOFUEL_CAPACITY_MLPY)
    lo = max(y for y in anchors if y <= year)
    hi = min(y for y in anchors if y >= year)
    if lo == hi:
        return BIOFUEL_CAPACITY_MLPY[lo][index]
    a, b = BIOFUEL_CAPACITY_MLPY[lo][index], BIOFUEL_CAPACITY_MLPY[hi][index]
    return a + (b - a) * (year - lo) / (hi - lo)


def biofuel_envelope_pj(year: int) -> float:
    biodiesel = interpolate_milestones(year, 0)
    ethanol = interpolate_milestones(year, 1)
    return BIOFUEL_UTILIZATION * (
        biodiesel * BIODIESEL_MJ_PER_L + ethanol * BIOETHANOL_MJ_PER_L
    ) / 1000


def mutate_structure(gen):
    tech_id, by_id = tech_maps(gen)
    commodity_id, _ = comm_maps(gen)
    # Reliability is represented through existing peak-timeslice capacity
    # equations, not a new cross-technology annual activity constraint.  This
    # keeps expansion endogenous and avoids the r6 presolve regression.

    # The high/low-wind labels carry identical YearSplit, demand profiles and
    # all but two isolated 2020 CF cells.  Remove the redundant daytype and its
    # 12 timeslices here so UpdateCase regenerates every source table from the
    # smaller structural set.  overlay_parameters performs a lossless weighted
    # aggregation of the removed pairs into the retained timeslices.
    removed_timeslices = {
        row["TsId"] for row in gen["osy-ts"] if row["DT"] == REDUNDANT_DAYTYPE_ID
    }
    gen["osy-dt"] = [row for row in gen["osy-dt"] if row["DtId"] != REDUNDANT_DAYTYPE_ID]
    gen["osy-ts"] = [row for row in gen["osy-ts"] if row["TsId"] not in removed_timeslices]
    for row in gen["osy-dt"]:
        if row["DtId"] == REPRESENTATIVE_DAYTYPE_ID:
            row["Desc"] = "Representative day"
    for row in gen["osy-ts"]:
        row["Desc"] = row["Desc"].replace("low wind", "representative")

    # Close three free-energy agriculture-heat routes. Membership is a
    # structural source change and therefore precedes UpdateCase regeneration.
    for name, (commodity, _) in AGRICULTURE_HEAT_IAR.items():
        tech = by_id[tech_id[name]]
        cid = commodity_id[commodity]
        if cid not in tech["IAR"]:
            tech["IAR"].append(cid)

    crop_names = []
    for tech in gen["osy-tech"]:
        name = tech["Tech"]
        is_crop = name.startswith("LND") and name.endswith("TOT") and any(
            token in name for token in ("RCP", "MZE", "CON", "TOM", "SGC", "OTH")
        ) and name != "LNDOTHTOT"
        if is_crop:
            crop_names.append(name)

    # AFOLU is published from solved physical activities.  No emissions
    # membership, accounting terminal or equality is added to the LP.
    coefficients = afolu_coefficients(crop_names)
    for name, accounting in AFOLU_ACCOUNTING.items():
        if not any(t["Tech"] == name for t in gen["osy-tech"]):
            gen["osy-tech"].append({
                "TechId": accounting["tech_id"],
                "Tech": name,
                "Desc": "Non-forcing AFOLU emissions accounting terminal; activity exactly mirrors endogenous land activity.",
                "CapUnitId": "accounting capacity",
                "ActUnitId": "MTon",
                "TG": [], "IAR": [], "OAR": [], "INCR": [], "ITCR": [], "EAR": [CO2E],
            })
        if not any(c["ConId"] == accounting["constraint_id"] for c in gen["osy-constraints"]):
            gen["osy-constraints"].append({
                "ConId": accounting["constraint_id"],
                "Con": f"BAL_{name}",
                "Desc": "Accounting identity only: terminal activity equals endogenous source land activity.",
                "Tag": 1,
                "CM": [tech_id[source] for source in coefficients[name]] + [accounting["tech_id"]],
            })

    by_id[tech_id["PHL_HOU_COOK_COAL"]]["Desc"] = (
        "Household charcoal cooking represented through the inherited coal-labelled proxy; "
        "retain as charcoal until a dedicated charcoal commodity chain is introduced."
    )
    return crop_names


def inherit_or_tighten(table, parameter, tech_id, years, value_by_year):
    base_row = select_row(table[parameter][BASE], tech_id)
    for year in years:
        base_row[year] = value_by_year[year]
    for scenario, rows in table[parameter].items():
        if scenario == BASE:
            continue
        row = select_row(rows, tech_id)
        for year in years:
            current = row[year]
            ceiling = value_by_year[year]
            if current is None or abs(float(current)) >= 9999:
                row[year] = None
            elif parameter == "TAMaxCI" and float(current) > float(ceiling):
                row[year] = ceiling


def overlay_parameters(target: Path, crop_names: list[str]):
    gen = read_json(target / "genData.json")
    source_gen = read_json(SOURCE / "genData.json")
    tech_id, _ = tech_maps(gen)
    comm_id, _ = comm_maps(gen)

    source_ts = source_gen["osy-ts"]
    source_ts_by_key = {
        (row["SE"], row["DTB"], row["DT"]): row["TsId"] for row in source_ts
    }
    retained_pairs = {}
    for row in gen["osy-ts"]:
        if row["SE"] == "SE_ugd96":
            continue
        retained_pairs[row["TsId"]] = (
            source_ts_by_key[(row["SE"], row["DTB"], REPRESENTATIVE_DAYTYPE_ID)],
            source_ts_by_key[(row["SE"], row["DTB"], REDUNDANT_DAYTYPE_ID)],
        )

    # Collapse the information-free high/low-wind daytype losslessly.  YearSplit
    # and demand-profile weights are summed; capacity factors are YearSplit-
    # weighted averages.  Worst-day timeslices are unchanged.
    source_ryts = read_json(SOURCE / "RYTs.json")
    ryts = read_json(target / "RYTs.json")
    source_ys = {row["TsId"]: row for row in source_ryts["YS"][BASE]}
    candidate_ys = {row["TsId"]: row for row in ryts["YS"][BASE]}
    for retained, pair in retained_pairs.items():
        for year in YEARS:
            candidate_ys[retained][year] = sum(float(source_ys[ts][year]) for ts in pair)
    for scenario, rows in ryts["YS"].items():
        if scenario != BASE:
            for row in rows:
                for year in YEARS:
                    row[year] = None
    write_json(target / "RYTs.json", ryts)

    if SCOPE_ONLY:
        # Calibrate physical end-use conversion drivers without prescribing
        # observed technology activity or fuel shares.
        rytcm = read_json(target / "RYTCM.json")
        changed_coordinates = set()
        for name, efficiency in COOKING_EFFICIENCY.items():
            rows = [r for r in rytcm["IAR"][BASE] if r["TechId"] == tech_id[name]]
            if not rows:
                raise AssertionError(f"missing cooking IAR rows for {name}")
            for row in rows:
                changed_coordinates.add((row["TechId"], row["CommId"]))
                for year in YEARS:
                    row[year] = 1.0 / efficiency if row["MoId"] == 1 else 0.0
        for name, (commodity, coefficient) in AGRICULTURE_HEAT_IAR.items():
            rows = [
                r for r in rytcm["IAR"][BASE]
                if r["TechId"] == tech_id[name] and r["CommId"] == comm_id[commodity]
            ]
            if not rows:
                raise AssertionError(f"missing agriculture-heat IAR rows for {name}/{commodity}")
            for row in rows:
                changed_coordinates.add((row["TechId"], row["CommId"]))
                for year in YEARS:
                    row[year] = coefficient if row["MoId"] == 1 else 0.0
        for scenario, rows in rytcm["IAR"].items():
            if scenario == BASE:
                continue
            for row in rows:
                if (row["TechId"], row["CommId"]) in changed_coordinates:
                    for year in YEARS:
                        row[year] = None
        write_json(target / "RYTCM.json", rytcm)

        # Lossless capacity-factor aggregation into each retained timeslice.
        rytts = read_json(target / "RYTTs.json")
        source_rytts = read_json(SOURCE / "RYTTs.json")
        source_cf = {(r["TechId"], r["TsId"]): r for r in source_rytts["CF"][BASE]}
        for row in rytts["CF"][BASE]:
            retained = row["TsId"]
            if retained not in retained_pairs:
                continue
            lo, hi = retained_pairs[retained]
            for year in YEARS:
                lw, hw = float(source_ys[lo][year]), float(source_ys[hi][year])
                row[year] = (
                    float(source_cf[(row["TechId"], lo)][year]) * lw
                    + float(source_cf[(row["TechId"], hi)][year]) * hw
                ) / (lw + hw)
        for scenario, rows in rytts["CF"].items():
            if scenario != BASE:
                for row in rows:
                    for year in YEARS:
                        row[year] = None
        write_json(target / "RYTTs.json", rytts)

        # Demand-profile weights are additive; every commodity-year remains
        # normalized after summing the redundant high/low-wind pair.
        rycts = read_json(target / "RYCTs.json")
        source_rycts = read_json(SOURCE / "RYCTs.json")
        source_sdp = {(r["CommId"], r["TsId"]): r for r in source_rycts["SDP"][BASE]}
        for row in rycts["SDP"][BASE]:
            retained = row["TsId"]
            if retained not in retained_pairs:
                continue
            lo, hi = retained_pairs[retained]
            for year in YEARS:
                row[year] = (
                    float(source_sdp[(row["CommId"], lo)][year])
                    + float(source_sdp[(row["CommId"], hi)][year])
                )
        for scenario, rows in rycts["SDP"].items():
            if scenario != BASE:
                for row in rows:
                    for year in YEARS:
                        row[year] = None
        write_json(target / "RYCTs.json", rycts)
        return

    ryt = read_json(target / "RYT.json")
    # Fixed, deliberately oversized accounting throughput.  These are not
    # physical investments and cannot bind any land outcome.
    for accounting in AFOLU_ACCOUNTING.values():
        tid = accounting["tech_id"]
        inherit_or_tighten(ryt, "TAMaxCI", tid, YEARS, {year: 0.0 for year in YEARS})
        residual = select_row(ryt["RC"][BASE], tid)
        for year in YEARS:
            residual[year] = 1.0
        for scenario, rows in ryt["RC"].items():
            if scenario == BASE:
                continue
            other = select_row(rows, tid)
            for year in YEARS:
                other[year] = None
    # Initial year is an initial stock condition, not an investment decision.
    for name in PRE2026_BUILD_GW:
        values = {"2020": 0.0}
        values.update({str(y): PRE2026_BUILD_GW[name] for y in range(2021, 2026)})
        inherit_or_tighten(ryt, "TAMaxCI", tech_id[name], tuple(values), values)

    for name in FULL_HORIZON_CLOSED:
        values = {year: 0.0 for year in YEARS}
        inherit_or_tighten(ryt, "TAMaxCI", tech_id[name], YEARS, values)
    for name in CCS_BEFORE_2030_CLOSED:
        years = tuple(str(y) for y in range(2020, 2030))
        values = {year: 0.0 for year in years}
        inherit_or_tighten(ryt, "TAMaxCI", tech_id[name], years, values)

    bio_values = {year: biofuel_envelope_pj(int(year)) for year in YEARS}
    inherit_or_tighten(ryt, "TAU", tech_id["PHL_PRO_PROC_BIOF"], YEARS, bio_values)

    for name, availability in NEW_THERMAL_AF.items():
        row = select_row(ryt["AF"][BASE], tech_id[name])
        for year in YEARS:
            row[year] = availability
        for scenario, rows in ryt["AF"].items():
            if scenario == BASE:
                continue
            other = select_row(rows, tech_id[name])
            for year in YEARS:
                other[year] = None
    write_json(target / "RYT.json", ryt)

    rt = read_json(target / "RT.json")
    for scenario, values in rt["CAU"].items():
        for accounting in AFOLU_ACCOUNTING.values():
            values[0][accounting["tech_id"]] = 20000.0 if scenario == BASE else None
    write_json(target / "RT.json", rt)

    rytm = read_json(target / "RYTM.json")
    for row in rytm["VC"][BASE]:
        if row["TechId"] == tech_id["PHL_PRO_PROC_BIOF"]:
            for year in YEARS:
                row[year] = BIOFUEL_COST_MUSD_PER_PJ
    for scenario, rows in rytm["VC"].items():
        if scenario == BASE:
            continue
        for row in rows:
            if row["TechId"] == tech_id["PHL_PRO_PROC_BIOF"]:
                for year in YEARS:
                    row[year] = None
    write_json(target / "RYTM.json", rytm)

    rytcm = read_json(target / "RYTCM.json")
    water = comm_id["PHL_PWR_WAT"]
    for name, gal_mwh in COOLING_GAL_MWH.items():
        rows = [r for r in rytcm["IAR"][BASE] if r["TechId"] == tech_id[name] and r["CommId"] == water]
        for row in rows:
            for year in YEARS:
                row[year] = gal_mwh * GAL_MWH_TO_KM3_PJ if row["MoId"] == 1 else 0.0
    td_rows = [r for r in rytcm["IAR"][BASE]
               if r["TechId"] == tech_id["PHL_POW_TD"] and r["CommId"] == comm_id["PHL_POW_ELE"]]
    for row in td_rows:
        for year in YEARS:
            row[year] = TD_INPUT_PER_OUTPUT if row["MoId"] == 1 else 0.0
    agr_ground = [r for r in rytcm["IAR"][BASE]
                  if r["TechId"] == tech_id["DEMAGRGWTPHL"] and r["CommId"] == comm_id["PHL_AGR_ELE"]]
    for row in agr_ground:
        for year in YEARS:
            row[year] = 0.70 if row["MoId"] == 1 else 0.0
    cooking_coordinates = set()
    for name, efficiency in COOKING_EFFICIENCY.items():
        rows = [r for r in rytcm["IAR"][BASE] if r["TechId"] == tech_id[name]]
        if not rows:
            raise AssertionError(f"missing cooking IAR rows for {name}")
        for row in rows:
            cooking_coordinates.add((row["TechId"], row["CommId"]))
            for year in YEARS:
                row[year] = 1.0 / efficiency if row["MoId"] == 1 else 0.0
    affected_coordinates = {
        (tech_id[name], water) for name in COOLING_GAL_MWH
    } | {
        (tech_id["PHL_POW_TD"], comm_id["PHL_POW_ELE"]),
        (tech_id["DEMAGRGWTPHL"], comm_id["PHL_AGR_ELE"]),
    } | cooking_coordinates
    for parameter in ("IAR",):
        for scenario, rows in rytcm[parameter].items():
            if scenario == BASE:
                continue
            for row in rows:
                if (row["TechId"], row["CommId"]) in affected_coordinates:
                    for year in YEARS:
                        row[year] = None
    write_json(target / "RYTCM.json", rytcm)

    # First aggregate each removed high/low pair, then rotate the UTC-indexed
    # solar series by two four-hour brackets to Philippine local time.
    rytts = read_json(target / "RYTTs.json")
    source_rytts = read_json(SOURCE / "RYTTs.json")
    source_cf = {
        (r["TechId"], r["TsId"]): r for r in source_rytts["CF"][BASE]
    }
    candidate_cf = {
        (r["TechId"], r["TsId"]): r for r in rytts["CF"][BASE]
    }
    for (tid, retained), row in candidate_cf.items():
        if retained not in retained_pairs:
            continue
        lo, hi = retained_pairs[retained]
        for year in YEARS:
            lo_weight = float(source_ys[lo][year])
            hi_weight = float(source_ys[hi][year])
            row[year] = (
                float(source_cf[(tid, lo)][year]) * lo_weight
                + float(source_cf[(tid, hi)][year]) * hi_weight
            ) / (lo_weight + hi_weight)
    solar_rows = {r["TsId"]: r for r in rytts["CF"][BASE] if r["TechId"] == tech_id["PHL_POW_PP_SPV"]}
    ts_order = [x["TsId"] for x in sorted(gen["osy-ts"], key=lambda z: int(z["Ts"]))]
    regular_seasons = [row["SeId"] for row in gen["osy-se"] if row["SeId"] != "SE_ugd96"]
    for season in regular_seasons:
        block = [row["TsId"] for row in sorted(gen["osy-ts"], key=lambda z: int(z["Ts"])) if row["SE"] == season]
        for year in YEARS:
            old = [solar_rows[ts][year] for ts in block]
            rotated = [old[4], old[5], old[0], old[1], old[2], old[3]]
            for ts, value in zip(block, rotated):
                solar_rows[ts][year] = value
    # The explicit worst-day peak uses dependable capacity divided by the DOE
    # planning-reserve factor.  This changes a physical availability driver;
    # it does not prescribe a technology build or market share.
    worst = [row["TsId"] for row in sorted(gen["osy-ts"], key=lambda z: int(z["Ts"])) if row["SE"] == "SE_ugd96"]
    peak_ts = worst[4]
    for name, credit in CAPACITY_CREDIT.items():
        row = next(r for r in rytts["CF"][BASE]
                   if r["TechId"] == tech_id[name] and r["TsId"] == peak_ts)
        for year in YEARS:
            row[year] = min(float(row[year]), credit / PLANNING_RESERVE_FACTOR)
    for scenario, rows in rytts["CF"].items():
        if scenario == BASE:
            continue
        for row in rows:
            if row["TechId"] in {tech_id[name] for name in CAPACITY_CREDIT}:
                for year in YEARS:
                    row[year] = None
    write_json(target / "RYTTs.json", rytts)

    # Make the explicit worst day contain the observed peak while preserving
    # every commodity's annual profile normalization.
    rycts = read_json(target / "RYCTs.json")
    source_rycts = read_json(SOURCE / "RYCTs.json")
    source_sdp = {(r["CommId"], r["TsId"]): r for r in source_rycts["SDP"][BASE]}
    for row in rycts["SDP"][BASE]:
        retained = row["TsId"]
        if retained not in retained_pairs:
            continue
        lo, hi = retained_pairs[retained]
        for year in YEARS:
            row[year] = float(source_sdp[(row["CommId"], lo)][year]) + float(source_sdp[(row["CommId"], hi)][year])
    ys = {r["TsId"]: r for r in ryts["YS"][BASE]}
    common_id = comm_id["PHL_HOU_ELEF"]
    common = {r["TsId"]: r for r in rycts["SDP"][BASE] if r["CommId"] == common_id}
    profiled_commodities = []
    all_by_comm = {}
    for row in rycts["SDP"][BASE]:
        all_by_comm.setdefault(row["CommId"], {})[row["TsId"]] = row
    for commodity, rows in all_by_comm.items():
        if all(abs(float(rows[ts]["2020"]) - float(common[ts]["2020"])) < 1e-12 for ts in common):
            profiled_commodities.append(commodity)
    peak_ts = worst[4]
    for commodity in profiled_commodities:
        rows = all_by_comm[commodity]
        for year in YEARS:
            old_peak = float(rows[peak_ts][year])
            new_peak = PEAK_TO_AVERAGE * float(ys[peak_ts][year])
            delta = new_peak - old_peak
            donor_total = sum(float(rows[ts][year]) for ts in worst if ts != peak_ts)
            for ts in worst:
                if ts == peak_ts:
                    rows[ts][year] = new_peak
                else:
                    rows[ts][year] = float(rows[ts][year]) - delta * float(rows[ts][year]) / donor_total
    for scenario, rows in rycts["SDP"].items():
        if scenario == BASE:
            continue
        for row in rows:
            if row["CommId"] in profiled_commodities:
                for year in YEARS:
                    row[year] = None
    write_json(target / "RYCTs.json", rycts)

    # Rice methane, managed-soil N2O, and partial land-stock change accounting.
    # All modes of each terminal carry the same factor, so redistribution among
    # its otherwise abstract modes cannot change total emissions.
    rytem = read_json(target / "RYTEM.json")
    terminal_ids = {accounting["tech_id"] for accounting in AFOLU_ACCOUNTING.values()}
    by_terminal = {accounting["tech_id"]: accounting for accounting in AFOLU_ACCOUNTING.values()}
    for parameter in ("EAR", "EACR"):
        for row in rytem[parameter][BASE]:
            if row["TechId"] not in terminal_ids or row["EmisId"] != CO2E:
                continue
            factor = by_terminal[row["TechId"]]["ear" if parameter == "EAR" else "eacr"]
            for year in YEARS:
                row[year] = factor
    for scenario in rytem["EAR"]:
        if scenario == BASE:
            continue
        for parameter in ("EAR", "EACR"):
            for row in rytem[parameter][scenario]:
                if row["TechId"] in terminal_ids and row["EmisId"] == CO2E:
                    for year in YEARS:
                        row[year] = None
    write_json(target / "RYTEM.json", rytem)

    # No case-specific adequacy UDC is added.  Reliability is carried by the
    # existing peak-timeslice capacity equations and the CF derating above.
    rycn = read_json(target / "RYCn.json")
    for accounting in AFOLU_ACCOUNTING.values():
        row = next(r for r in rycn["UCC"][BASE] if r["ConId"] == accounting["constraint_id"])
        for year in YEARS:
            row[year] = 0.0
        for scenario, rows in rycn["UCC"].items():
            if scenario == BASE:
                continue
            other = next(r for r in rows if r["ConId"] == accounting["constraint_id"])
            for year in YEARS:
                other[year] = None
    write_json(target / "RYCn.json", rycn)

    rytcn = read_json(target / "RYTCn.json")
    sources = afolu_coefficients(crop_names)
    for name, accounting in AFOLU_ACCOUNTING.items():
        coefficients = {tech_id[source]: value for source, value in sources[name].items()}
        coefficients[accounting["tech_id"]] = -1.0
        for tid, coefficient in coefficients.items():
            for parameter, value in (("CAM", coefficient), ("CCM", 0.0), ("CNCM", 0.0)):
                row = select_row(rytcn[parameter][BASE], tid, ConId=accounting["constraint_id"])
                for year in YEARS:
                    row[year] = value
                for scenario, rows in rytcn[parameter].items():
                    if scenario == BASE:
                        continue
                    other = select_row(rows, tid, ConId=accounting["constraint_id"])
                    for year in YEARS:
                        other[year] = None
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


def write_evidence_and_ledger(target: Path, crop_names: list[str], source_hashes: dict[str, str]):
    ledger = target / "data_sources"
    if ledger.exists():
        shutil.rmtree(ledger)
    shutil.copytree(LEDGER_BASE, ledger)
    evidence = ledger / "snapshots" / "philippines_v22_source_extracts_2026-08-20.json"
    extracts = {
        "schema": "philippines-v22-retained-source-extracts-v1",
        "access_date": "2026-08-20",
        "download_note": "Authoritative URLs, locators and the numerical facts used by this candidate are retained in this hashed extract.",
        "sources": {
            "DOE_PEP_2020_2040": {"url": "https://legacy.doe.gov.ph/sites/default/files/pdf/pep/PEP-2020-2040-Final%20eCopy-as-of-15-June-2023.pdf", "locator": "Table 32 and power-planning assumptions", "facts": {"biofuel_capacity_mlpy": BIOFUEL_CAPACITY_MLPY, "biofuel_capacity_utilization": BIOFUEL_UTILIZATION, "reserve_margin": 0.25}},
            "DOE_2020_POWER": {"url": "https://doe.gov.ph/site/epimb/articles/group/reports?category=Power+Situation+Report", "locator": "2020 Power Situation Report; 2020 Power Statistics", "facts": {"noncoincident_peak_mw": 15282, "electricity_consumption_gwh": 101756, "sales_gwh": 83243, "system_losses_gwh": 9742, "peak_to_average": PEAK_TO_AVERAGE}},
            "NREL_50900": {"url": "https://www.nrel.gov/docs/fy11osti/50900.pdf", "locator": "Table 3 water withdrawal factors", "facts": {"gal_per_mwh": COOLING_GAL_MWH, "conversion_km3_per_pj_per_gal_mwh": GAL_MWH_TO_KM3_PJ}},
            "PSA_WATER_2020": {"url": "https://psa.gov.ph/content/countrys-overall-water-use-efficiency-decreased-while-water-stress-remains-low-level?vcode=72", "locator": "2010-2020 Water Accounts release", "facts": {"surface_share_average": 0.981, "groundwater_share_average": 0.019, "classification": "benchmark only; not a model share constraint"}},
            "PHL_GHGI_2020": {"url": "https://niccdies.climate.gov.ph/files/documents/2015%20and%202020%20National%20GHGI%20Executive%20Brief.pdf", "locator": "Table 6", "facts": {"rice_cultivation_mtco2e": 26.985, "managed_soils_direct_mtco2e": 6.875, "managed_soils_indirect_mtco2e": 2.277, "agriculture_total_mtco2e": 54.080}},
            "IPCC_2019_AFOLU": {"url": "https://www.ipcc-nggip.iges.or.jp/public/2019rf/vol4.html", "locator": "Volume 4 AFOLU; Tier 1 stock-change method", "facts": {"implementation": "screening aboveground stock-change coefficients; incomplete soil/deadwood pools disclosed"}},
            "IRENA_BIOENERGY_2022": {"url": "https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2022/Aug/IRENA_Bioenergy_for_the_transition_2022.pdf", "locator": "transport biofuel wholesale cost ranges", "facts": {"bioethanol_usd_per_gj_range": [14, 32], "biodiesel_usd_per_gj_range": [22, 28], "model_midpoint_musd_per_pj": BIOFUEL_COST_MUSD_PER_PJ}},
            "PSA_CPH_2020": {"url": "https://psa.gov.ph/content/household-characteristics-2020-census-population-and-housing?vcode=-3", "locator": "Figure 4 and paragraph 11", "facts": {"lpg_percent": 47.9, "wood_percent": 32.2, "charcoal_percent": 7.2, "electricity_percent": 6.8, "kerosene_percent": 5.2, "classification": "initial-stock and validation evidence; not a future share constraint"}},
            "WORLD_BANK_COOKING_EFFICIENCY": {"url": "https://documents.worldbank.org/curated/en/380771468210887487/pdf/538770PUB0Bang101Official0Use0Only1.pdf", "locator": "Cooking Fuels and Energy Efficiencies table", "facts": {"efficiency": COOKING_EFFICIENCY, "classification": "generic engineering parameters used where Philippine stove test data are unavailable"}},
            "FAO_AQUASTAT_IWR_METHOD": {"url": "https://www.fao.org/aquastat/en/data-analysis/irrig-water-use/irrig-water-requirement/", "locator": "Irrigation water requirement definition and equation", "facts": {"benchmark_km3": IRRIGATION_REQUIREMENT_BENCHMARK_KM3, "boundary": "net irrigation requirement excluding conveyance, distribution and application losses"}},
        },
        "derived": {"biofuel_envelope_pj": {year: biofuel_envelope_pj(int(year)) for year in YEARS}, "td_input_per_output": TD_INPUT_PER_OUTPUT, "adequacy_activity_multiplier": ADEQUACY_ACTIVITY_MULTIPLIER, "rice_ch4_factor": RICE_CH4_FACTOR, "managed_soil_factor": MANAGED_SOIL_FACTOR},
    }
    write_json(evidence, extracts)
    digest = sha256(evidence)
    local = str(evidence.relative_to(ledger))

    sources = []
    source_defs = [
        ("SRC_PHL_V22_DOE_PEP", "Philippine Department of Energy", "Philippine Energy Plan 2020-2040", "Biofuel capacity and 25% reserve", extracts["sources"]["DOE_PEP_2020_2040"]["url"]),
        ("SRC_PHL_V22_DOE_POWER", "Philippine Department of Energy", "2020 Power Situation Report and Power Statistics", "Peak, consumption, sales and losses", extracts["sources"]["DOE_2020_POWER"]["url"]),
        ("SRC_PHL_V22_NREL_WATER", "NREL", "Review of Operational Water Consumption and Withdrawal Factors", "Cooling withdrawal medians", extracts["sources"]["NREL_50900"]["url"]),
        ("SRC_PHL_V22_PSA_WATER", "Philippine Statistics Authority", "Water Accounts of the Philippines", "Surface/groundwater abstraction benchmark", extracts["sources"]["PSA_WATER_2020"]["url"]),
        ("SRC_PHL_V22_GHGI", "Climate Change Commission NICCDIES", "2015 and 2020 National GHG Inventory Executive Brief", "Rice and managed-soil emissions", extracts["sources"]["PHL_GHGI_2020"]["url"]),
        ("SRC_PHL_V22_IPCC_AFOLU", "IPCC TFI", "2019 Refinement Volume 4 AFOLU", "Tier 1 land stock-change method", extracts["sources"]["IPCC_2019_AFOLU"]["url"]),
        ("SRC_PHL_V22_IRENA_BIOFUEL", "IRENA", "Bioenergy for the Energy Transition", "Biofuel wholesale cost ranges", extracts["sources"]["IRENA_BIOENERGY_2022"]["url"]),
        ("SRC_PHL_V22_PSA_CPH", "Philippine Statistics Authority", "2020 Census of Population and Housing household characteristics", "Primary cooking fuel shares", extracts["sources"]["PSA_CPH_2020"]["url"]),
        ("SRC_PHL_V22_WB_COOKING", "World Bank", "Cooking Fuels and Energy Efficiencies", "Typical cooking end-use efficiencies", extracts["sources"]["WORLD_BANK_COOKING_EFFICIENCY"]["url"]),
        ("SRC_PHL_V22_FAO_IWR", "FAO AQUASTAT", "Irrigation water requirement methodology", "Net irrigation-requirement accounting boundary", extracts["sources"]["FAO_AQUASTAT_IWR_METHOD"]["url"]),
        ("SRC_PHL_V22_SOURCE_CASE", "MUIOGO", "Philippines_v21 canonical source and accepted r4 result", "Immediate model lineage", ""),
    ]
    for sid, provider, product, variable, url in source_defs:
        sources.append({"source_id": sid, "provider": provider, "product": product, "edition": "retained 2026-08-20", "reference_period": "2020-2053", "geography": "Philippines", "variable": variable, "source_unit": "source-specific", "exact_locator": "See retained extract and cited source locator", "url": url, "access_date": "2026-08-20", "license": "Provider terms", "sha256": digest, "local_file": local, "notes": "Retained extract hash; see download note in snapshot."})
    append_csv(ledger / "SOURCES.csv", sources)

    assumptions = [
        {"assumption_id": "ASM_PHL_V22_NO_OUTCOME_FORCING", "statement": "Observed irrigation, groundwater, technology activity and market shares remain benchmarks; no equality or historical share is added.", "rationale": "Repository master rule."},
        {"assumption_id": "ASM_PHL_V22_BIOFUEL_AGGREGATE", "statement": "The existing no-input biofuel technology is treated as aggregate domestic supply, capped by accredited/planned production capacity and charged a midpoint production cost.", "central_value": BIOFUEL_COST_MUSD_PER_PJ, "unit": "MUSD/PJ", "evidence_source_ids": "SRC_PHL_V22_DOE_PEP;SRC_PHL_V22_IRENA_BIOFUEL", "rationale": "Minimal repair without inventing an unsourced feedstock chain."},
        {"assumption_id": "ASM_PHL_V22_NEW_THERMAL_AF", "statement": "New thermal planning availability is 0.80-0.90 by technology; legacy AF remains DOE dependable/nameplate.", "central_value": json.dumps(NEW_THERMAL_AF, sort_keys=True), "unit": "fraction", "evidence_source_ids": "SRC_PHL_V22_DOE_POWER", "rationale": "Remove perfect availability while retaining a transparent planning assumption."},
        {"assumption_id": "ASM_PHL_V22_CAPACITY_CREDIT", "statement": "Firm-capacity credits equal legacy dependability or new planning AF; wind/solar receive zero on the retained worst day.", "central_value": json.dumps(CAPACITY_CREDIT, sort_keys=True), "unit": "fraction", "evidence_source_ids": "SRC_PHL_V22_DOE_PEP;SRC_PHL_V22_DOE_POWER", "rationale": "Conservative adequacy accounting."},
        {"assumption_id": "ASM_PHL_V22_COOKING_EFFICIENCY", "statement": "Household fuel inputs are converted to useful cooking energy using World Bank typical end-use efficiencies; PHL_HOU_COOK_COAL remains the documented charcoal proxy.", "central_value": json.dumps(COOKING_EFFICIENCY, sort_keys=True), "unit": "useful PJ/fuel PJ", "evidence_source_ids": "SRC_PHL_V22_WB_COOKING;SRC_PHL_V22_PSA_CPH;SRC_PHL_V22_SOURCE_CASE", "rationale": "Replace the inherited 100% efficiency for every stove without prescribing a fuel choice."},
        {"assumption_id": "ASM_PHL_V22_DAYTYPE_COLLAPSE", "statement": "The duplicate high-wind daytype is removed; YearSplit and SDP are summed and CF is YearSplit-weighted into the retained representative timeslice.", "evidence_source_ids": "SRC_PHL_V22_SOURCE_CASE", "rationale": "All low/high pairs are identical except two isolated 2020 agriculture-heating CF cells; weighted aggregation preserves their annual contribution and removes no information."},
        {"assumption_id": "ASM_PHL_V22_LAND_STOCK_SCREEN", "statement": "Land-use change uses partial Tier-1 screening carbon stocks and omits soil, deadwood and harvested wood products.", "central_value": json.dumps(LAND_STOCK_MT_PER_1000KM2, sort_keys=True), "unit": "MtCO2/1000 km2", "evidence_source_ids": "SRC_PHL_V22_IPCC_AFOLU", "rationale": "Create a transparent land-climate link while disclosing incomplete pools."},
        {"assumption_id": "ASM_PHL_V22_AFOLU_POSTSOLVE", "statement": "Rice methane, managed-soil N2O and partial land-stock change are calculated and published post-solve from endogenous physical land activities; no AFOLU terminal, emissions membership, constraint, price or cap is added to the LP.", "evidence_source_ids": "SRC_PHL_V22_SOURCE_CASE;SRC_PHL_V22_GHGI;SRC_PHL_V22_IPCC_AFOLU", "rationale": "Preserve rice-specific reporting without expanding physical modes or feeding an accounting-only quantity back into decisions."},
    ]
    append_csv(ledger / "ASSUMPTIONS.csv", assumptions)

    calculations = [
        {"calculation_id": "CALC_PHL_V22_BIOFUEL_CAP", "formula": "0.8*(biodiesel MLPY*33.3 + bioethanol MLPY*21.2)/1000", "source_ids": "SRC_PHL_V22_DOE_PEP", "assumption_ids": "ASM_PHL_V22_BIOFUEL_AGGREGATE", "input_values": json.dumps(BIOFUEL_CAPACITY_MLPY, sort_keys=True), "input_units": "MLPY;MJ/L", "output_value": json.dumps({y: biofuel_envelope_pj(int(y)) for y in YEARS}, sort_keys=True), "output_unit": "PJ/year", "script_path": "scripts/build_philippines_v22_integrated_repair.py", "script_version": "v1"},
        {"calculation_id": "CALC_PHL_V22_COOLING", "formula": "gal/MWh * 3.785411784e-12 / 3.6e-6", "source_ids": "SRC_PHL_V22_NREL_WATER", "input_values": json.dumps(COOLING_GAL_MWH, sort_keys=True), "input_units": "gal/MWh", "output_value": json.dumps({k: v * GAL_MWH_TO_KM3_PJ for k, v in COOLING_GAL_MWH.items()}, sort_keys=True), "output_unit": "km3/PJ", "script_path": "scripts/build_philippines_v22_integrated_repair.py", "script_version": "v1"},
        {"calculation_id": "CALC_PHL_V22_TD", "formula": "(sales + system losses)/sales", "source_ids": "SRC_PHL_V22_DOE_POWER", "input_values": "83243;9742", "input_units": "GWh", "output_value": TD_INPUT_PER_OUTPUT, "output_unit": "PJ/PJ", "script_path": "scripts/build_philippines_v22_integrated_repair.py", "script_version": "v1"},
        {"calculation_id": "CALC_PHL_V22_ADEQUACY", "formula": "(peak/average)*1.25/31.536", "source_ids": "SRC_PHL_V22_DOE_PEP;SRC_PHL_V22_DOE_POWER", "assumption_ids": "ASM_PHL_V22_CAPACITY_CREDIT", "input_values": "15282 MW;101756 GWh;1.25", "input_units": "MW;GWh;fraction", "output_value": ADEQUACY_ACTIVITY_MULTIPLIER, "output_unit": "GW per PJ/year", "script_path": "scripts/build_philippines_v22_integrated_repair.py", "script_version": "v1"},
        {"calculation_id": "CALC_PHL_V22_COOKING_IAR", "formula": "fuel input per useful output = 1 / end-use efficiency", "source_ids": "SRC_PHL_V22_WB_COOKING", "assumption_ids": "ASM_PHL_V22_COOKING_EFFICIENCY", "input_values": json.dumps(COOKING_EFFICIENCY, sort_keys=True), "input_units": "useful PJ/fuel PJ", "output_value": json.dumps({k: 1 / v for k, v in COOKING_EFFICIENCY.items()}, sort_keys=True), "output_unit": "fuel PJ/useful PJ", "script_path": "scripts/build_philippines_v22_integrated_repair.py", "script_version": "v1"},
        {"calculation_id": "CALC_PHL_V22_RICE_CH4", "formula": "26.985 MtCO2e / 34.7144 model land units", "source_ids": "SRC_PHL_V22_GHGI;SRC_PHL_V22_SOURCE_CASE", "input_values": "26.985;34.7144", "input_units": "MtCO2e;1000 km2", "output_value": RICE_CH4_FACTOR, "output_unit": "MtCO2e/1000 km2-year", "script_path": "scripts/build_philippines_v22_integrated_repair.py", "script_version": "v1"},
        {"calculation_id": "CALC_PHL_V22_SOIL_N2O", "formula": "(6.875+2.277) MtCO2e / 119.9929 model cropland units", "source_ids": "SRC_PHL_V22_GHGI;SRC_PHL_V22_SOURCE_CASE", "input_values": "6.875;2.277;119.9929", "input_units": "MtCO2e;1000 km2", "output_value": MANAGED_SOIL_FACTOR, "output_unit": "MtCO2e/1000 km2-year", "script_path": "scripts/build_philippines_v22_integrated_repair.py", "script_version": "v1"},
    ]
    append_csv(ledger / "CALCULATIONS.csv", calculations)

    maps = [
        {"map_id": "MAP_PHL_V22_BIOFUEL", "model_file": "RYT.json;RYTM.json", "parameter": "TAU;VC", "entity": "PHL_PRO_PROC_BIOF", "mode": "all", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "CALC_PHL_V22_BIOFUEL_CAP;24.5", "model_unit": "PJ/year;MUSD/PJ", "evidence_ids": "SRC_PHL_V22_DOE_PEP;SRC_PHL_V22_IRENA_BIOFUEL;CALC_PHL_V22_BIOFUEL_CAP;ASM_PHL_V22_BIOFUEL_AGGREGATE", "evidence_type": "derived"},
        {"map_id": "MAP_PHL_V22_COOLING", "model_file": "RYTCM.json", "parameter": "IAR", "entity": ";".join(COOLING_GAL_MWH), "mode": "all", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "CALC_PHL_V22_COOLING", "model_unit": "km3/PJ", "evidence_ids": "SRC_PHL_V22_NREL_WATER;CALC_PHL_V22_COOLING", "evidence_type": "derived"},
        {"map_id": "MAP_PHL_V22_TD", "model_file": "RYTCM.json", "parameter": "IAR", "entity": "PHL_POW_TD", "mode": "all", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": str(TD_INPUT_PER_OUTPUT), "model_unit": "PJ/PJ", "evidence_ids": "SRC_PHL_V22_DOE_POWER;CALC_PHL_V22_TD", "evidence_type": "derived"},
        {"map_id": "MAP_PHL_V22_PRE2026_BUILD", "model_file": "RYT.json", "parameter": "TAMaxCI", "entity": ";".join(PRE2026_BUILD_GW), "scenario": "SC_0 with inheritance", "years": "2020-2025", "value_or_expression": json.dumps(PRE2026_BUILD_GW, sort_keys=True), "model_unit": "GW/year", "evidence_ids": "SRC_PHL_V22_DOE_POWER;ASM_PHL_V22_NO_OUTCOME_FORCING", "evidence_type": "assumption"},
        {"map_id": "MAP_PHL_V22_SOLAR_LOCAL", "model_file": "RYTTs.json", "parameter": "CF", "entity": "PHL_POW_PP_SPV", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "two regular-season six-bracket blocks rotated +8 hours after daytype aggregation; annual weighted mean unchanged", "model_unit": "fraction", "evidence_ids": "SRC_PHL_V22_SOURCE_CASE", "evidence_type": "derived"},
        {"map_id": "MAP_PHL_V22_WORST_DAY", "model_file": "RYCTs.json", "parameter": "SDP", "entity": "commodities using common Philippine load profile", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": f"worst-day peak/average={PEAK_TO_AVERAGE}; annual profile sum unchanged", "model_unit": "fraction", "evidence_ids": "SRC_PHL_V22_DOE_POWER;CALC_PHL_V22_ADEQUACY", "evidence_type": "derived"},
        {"map_id": "MAP_PHL_V22_ADEQUACY", "model_file": "RYTTs.json;RYCTs.json", "parameter": "CF;SDP", "entity": "existing worst-day grid technologies and common electricity load profile", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "peak CF <= dependable-capacity credit/1.25; peak SDP/YearSplit = observed peak/average", "model_unit": "fraction", "evidence_ids": "SRC_PHL_V22_DOE_PEP;SRC_PHL_V22_DOE_POWER;CALC_PHL_V22_ADEQUACY;ASM_PHL_V22_CAPACITY_CREDIT", "evidence_type": "derived native-parameter formulation"},
        {"map_id": "MAP_PHL_V22_COOKING", "model_file": "RYTCM.json", "parameter": "IAR", "entity": ";".join(COOKING_EFFICIENCY), "mode": "1", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "CALC_PHL_V22_COOKING_IAR", "model_unit": "fuel PJ/useful PJ", "evidence_ids": "SRC_PHL_V22_WB_COOKING;SRC_PHL_V22_PSA_CPH;CALC_PHL_V22_COOKING_IAR;ASM_PHL_V22_COOKING_EFFICIENCY", "evidence_type": "derived"},
        {"map_id": "MAP_PHL_V22_DAYTYPE", "model_file": "genData.json;RYTs.json;RYCTs.json;RYTTs.json", "parameter": "DAYTYPE;TIMESLICE;YearSplit;SDP;CF", "entity": "DT_ii6mj and its 12 timeslices", "scenario": "all", "years": "2020-2053", "value_or_expression": "remove duplicate; retained YS=low+high, SDP=low+high, CF=YS-weighted mean", "model_unit": "mixed", "evidence_ids": "SRC_PHL_V22_SOURCE_CASE;ASM_PHL_V22_DAYTYPE_COLLAPSE", "evidence_type": "lossless structural aggregation"},
        {"map_id": "MAP_PHL_V22_AFOLU_IDENTITIES", "model_file": "res/INTEGRATED_REPAIR_V22_BASE/afolu_postsolve.csv", "parameter": "disclosed post-solve crop-activity GHG", "entity": ";".join(crop_names), "mode": "annual total", "scenario": "BASE", "years": "2020-2053", "value_or_expression": "sum endogenous crop activity * (managed-soil factor + rice methane factor where applicable)", "model_unit": "MtCO2e/year", "evidence_ids": "ASM_PHL_V22_NO_OUTCOME_FORCING;ASM_PHL_V22_AFOLU_POSTSOLVE", "evidence_type": "disclosed post-solve accounting"},
        {"map_id": "MAP_PHL_V22_AFOLU_EAR", "model_file": "res/INTEGRATED_REPAIR_V22_BASE/afolu_postsolve.csv", "parameter": "crop_activity_ghg_mtco2e", "entity": ";".join(crop_names), "mode": "annual total", "scenario": "BASE", "years": "2020-2053", "value_or_expression": "CALC_PHL_V22_RICE_CH4 + CALC_PHL_V22_SOIL_N2O", "model_unit": "MtCO2e/year", "evidence_ids": "SRC_PHL_V22_GHGI;CALC_PHL_V22_RICE_CH4;CALC_PHL_V22_SOIL_N2O", "evidence_type": "disclosed post-solve accounting"},
        {"map_id": "MAP_PHL_V22_AFOLU_EACR", "model_file": "res/INTEGRATED_REPAIR_V22_BASE/afolu_postsolve.csv", "parameter": "disclosed post-solve land-stock change", "entity": "crop land options;LNDFORTOT;LNDGRSTOT;LNDOTHTOT", "mode": "annual total", "scenario": "BASE", "years": "2020-2053", "value_or_expression": "-change(sum endogenous land activity * partial carbon stock)", "model_unit": "MtCO2e/year", "evidence_ids": "SRC_PHL_V22_IPCC_AFOLU;ASM_PHL_V22_LAND_STOCK_SCREEN;ASM_PHL_V22_AFOLU_POSTSOLVE", "evidence_type": "disclosed post-solve accounting"},
    ]
    append_csv(ledger / "MODEL_MAP.csv", maps)

    gaps = [
        {"item": "AQUASTAT net irrigation requirement mismatch", "why_absent": "AQUASTAT's 33.28 km3 is a net crop requirement excluding delivery losses. Model delivery is 0.38 times gross withdrawal, so the solved 15.67 km3 delivery and 41.22 km3 withdrawal must not be compared as the same boundary or scaled to the benchmark.", "upgrade_source": "NIA scheme diversions, effective irrigated area, crop calendars, field application, conveyance and return flows reconciled to the AQUASTAT net boundary.", "priority": "high", "notes": "No irrigation demand, area or activity equality is added; gross, delivered and benchmark values are published separately."},
        {"item": "Groundwater source split", "why_absent": "PSA 1.9% is an aggregate observed outcome, not a sectoral physical capacity. Fixed source shares would violate the master rule.", "upgrade_source": "NWRB source/use permit capacities, aquifer safe yields, pumping depths and source-specific costs by service area.", "priority": "high", "notes": "Agricultural groundwater pumping energy is corrected; source choice remains endogenous and may be zero."},
        {"item": "Livestock emissions", "why_absent": "No livestock production/activity sector exists in the model.", "upgrade_source": "Add physical livestock stocks, products, feed and manure systems before applying inventory factors.", "priority": "high", "notes": "Rice, managed soils and land stock changes are added; agriculture coverage is partial."},
        {"item": "Cooling source seawater/freshwater split", "why_absent": "Generic power technologies do not identify plant cooling water source or location.", "upgrade_source": "Plant-level cooling technology and intake source register.", "priority": "high", "notes": "NREL withdrawal factors replace order-of-magnitude errors; freshwater accounting remains conservative."},
        {"item": "Dedicated charcoal supply chain", "why_absent": "The inherited coal-labelled household technology is a documented charcoal proxy, and its upstream commodity still cannot distinguish charcoal from mineral coal.", "upgrade_source": "Add charcoal production, trade, price and stove technologies as separate physical objects.", "priority": "high", "notes": "The proxy is relabelled and given charcoal stove efficiency; it is not forced closed and its solved activity remains endogenous."},
        {"item": "Aggregate biofuel feedstocks and blending", "why_absent": "The minimal repair caps and prices aggregate supply but does not distinguish biodiesel/ethanol feedstocks or gasoline/diesel mandates.", "upgrade_source": "Separate fuel commodities, crop/feedstock balances and legal blend equations.", "priority": "high", "notes": "No aggregate blend-share constraint is imposed."},
        {"item": "Partial land carbon pools", "why_absent": "The screening link omits soil, deadwood, litter and harvested wood products.", "upgrade_source": "Philippine land-transition matrix and inventory carbon pools.", "priority": "high", "notes": "Do not interpret screening EACR as a complete FOLU inventory."},
        {"item": "Other-land stock aggregation", "why_absent": "LNDOTHTOT combines model-defined other land with idle/fallow cropland, so post-solve technology-level activity cannot distinguish the component stocks.", "upgrade_source": "Split the adapter into separate physical technologies before assigning distinct stock factors.", "priority": "medium", "notes": "The disclosed post-solve screen applies the generic other-land stock to the aggregate; this is disclosed rather than hidden."},
    ]
    append_csv(ledger / "GAPS.csv", gaps)

    append_csv(ledger / "CHANGES.csv", [{"change_id": "CHG_PHL_V22_INTEGRATED_REPAIR_20260820", "date": str(date(2026, 8, 20)), "class": "B", "description": "Added non-forcing supply, native-parameter timing/reliability, cooking-efficiency, water and disclosed AFOLU repairs plus lossless daytype aggregation and a mandatory deterministic pre-run feasibility gate.", "model_objects": "genData.json;RYT.json;RYTM.json;RYTCM.json;RYTs.json;RYSeDt.json;RYTTs.json;RYCTs.json", "evidence_path": "calculation_notes/MODEL_FIXES_INTEGRATED_REPAIR_V22_2026-08-20.md", "map_rows_affected": ";".join(row["map_id"] for row in maps), "resolve_status": "candidate_pending_gate_and_solve", "author": "Codex", "commit": "", "notes": "No new UDC, observed endogenous activity, share, dispatch, irrigated area or source split is forced."}])

    notes = ledger / "calculation_notes" / "MODEL_FIXES_INTEGRATED_REPAIR_V22_2026-08-20.md"
    notes.write_text("""# Philippines v22 integrated physical repair — candidate design

This disposable candidate applies only reproducible source parameters and structural sets. Observed technology activity, fuel shares, irrigation volumes and groundwater shares remain validation benchmarks. The required order is: source build; deterministic gate; application generation and preprocessing; GLPK matrix check; one BASE optimization; then the explicitly requested active-policy validations. Nothing may be promoted without a proven optimal candidate and successful qualification checks.

## Physical changes

- Biofuel is an aggregate domestic supply route with a DOE production-capacity envelope and an IRENA-anchored cost. Oil remains an alternative; no blend share is forced.
- Pre-2026 power additions receive optional delivery ceilings. Thermal availability is below one, solar is shifted from UTC to Philippine local time, and the worst-day load and dependable-capacity derating use existing SDP/CF parameters and native commodity/capacity equations. No reliability UDC is added.
- The duplicate high/low-wind daytype is collapsed from 30 to 18 timeslices. YearSplit and SDP are summed and CF is YearSplit-weighted, preserving all annual information including the two non-identical 2020 agriculture-heating cells.
- NREL withdrawal medians replace erroneous cooling factors. Agricultural groundwater pumping energy is aligned with the existing public/power formulation. No groundwater share is imposed.
- Household cooking remains an endogenous stock-turnover choice. The coal-labelled technology is correctly disclosed as a charcoal proxy and is not closed; World Bank stove efficiencies replace the inherited 100% conversion for every fuel.
- Rice methane, managed-soil N2O and partial Tier-1 land-stock change are published after solving from endogenous physical land activity. They add no LP variable, membership, constraint, price or cap. Livestock is outside modeled scope because no physical livestock sector exists; national-agriculture inventory completeness is not claimed.

## Water boundary and master-rule treatment

AQUASTAT's 33.28 km3 figure is a net irrigation requirement excluding delivery losses. The model separately reports gross source withdrawal and 0.38-times-gross delivery; neither is forced to 33.28. PSA's 1.9% groundwater share is also benchmark-only. The deterministic gate checks every affected service, vintage, source and timeslice envelope before optimization and fails if this repair introduces any new UDC.

## Rejected designs

Direct CO2e membership on 24 crop technologies was rejected before optimization because MUIO expanded each membership across all 30 global modes (2,215,315 columns). Five- and two-terminal accounting designs were rejected by the matrix gate. A one-terminal design timed out at 360 seconds and was not promoted. The retained candidate has no AFOLU LP accounting and requires a fresh optimal solve before promotion.
""", encoding="utf-8")

    return {"ledger_snapshot": str(evidence), "ledger_snapshot_sha256": digest}


def write_scope_only_ledger(target: Path, crop_names: list[str], source_hashes: dict[str, str]):
    """Write the six-table ledger for the deliberately narrow r8 candidate."""
    ledger = target / "data_sources"
    if ledger.exists():
        shutil.rmtree(ledger)
    shutil.copytree(LEDGER_BASE, ledger)
    evidence = ledger / "snapshots" / "philippines_v22_transition_scope_extracts_2026-08-20.json"
    extracts = {
        "schema": "philippines-v22-transition-scope-retained-extracts-v1",
        "access_date": "2026-08-20",
        "source_case": str(SOURCE),
        "source_hashes": source_hashes,
        "facts": {
            "cooking_efficiency": COOKING_EFFICIENCY,
            "agriculture_heat_iar": AGRICULTURE_HEAT_IAR,
            "doe_2024_agriculture_forestry_fishery": {
                "total_ktoe": 438.8,
                "total_pj": AGRICULTURE_ENERGY_2024_PJ,
                "electricity_share": AGRICULTURE_ELECTRICITY_SHARE_2024,
                "classification": "validation benchmark only; no activity or share constraint",
            },
            "aquastat_irrigation_requirement_km3": IRRIGATION_REQUIREMENT_BENCHMARK_KM3,
            "aquastat_boundary": "net crop requirement excluding conveyance, distribution and application losses",
            "crop_ghgi_2020_mtco2e": {
                "rice_ch4": 26.985, "managed_soils_direct_n2o": 6.875,
                "managed_soils_indirect_n2o": 2.277,
            },
        },
        "urls": {
            "psa_cooking": "https://psa.gov.ph/content/household-characteristics-2020-census-population-and-housing?vcode=-3",
            "world_bank_efficiency": "https://documents.worldbank.org/curated/en/380771468210887487/pdf/538770PUB0Bang101Official0Use0Only1.pdf",
            "doe_2024": "https://legacy.doe.gov.ph/energy-statistics/philippine-energy-situationer",
            "fao_iwr": "https://www.fao.org/aquastat/en/data-analysis/irrig-water-use/irrig-water-requirement/",
            "ghgi": "https://niccdies.climate.gov.ph/files/documents/2015%20and%202020%20National%20GHGI%20Executive%20Brief.pdf",
            "ipcc_afolu": "https://www.ipcc-nggip.iges.or.jp/public/2019rf/vol4.html",
        },
    }
    write_json(evidence, extracts)
    digest = sha256(evidence)
    local = str(evidence.relative_to(ledger))
    source_rows = []
    for sid, provider, product, variable, url in [
        ("SRC_PHL_V22_SOURCE_CASE", "MUIOGO", "Philippines_v21 source and accepted r4 result", "model lineage", ""),
        ("SRC_PHL_V22_PSA_CPH", "Philippine Statistics Authority", "2020 CPH household characteristics", "cooking-fuel benchmark", extracts["urls"]["psa_cooking"]),
        ("SRC_PHL_V22_WB_COOKING", "World Bank", "Cooking Fuels and Energy Efficiencies", "cooking efficiency", extracts["urls"]["world_bank_efficiency"]),
        ("SRC_PHL_V22_DOE_2024_AFF", "Philippine Department of Energy", "2024 Philippine Energy Situationer", "agriculture/forestry/fishery energy benchmark", extracts["urls"]["doe_2024"]),
        ("SRC_PHL_V22_FAO_IWR", "FAO AQUASTAT", "Irrigation water requirement methodology", "net irrigation boundary", extracts["urls"]["fao_iwr"]),
        ("SRC_PHL_V22_GHGI", "Climate Change Commission NICCDIES", "2020 National GHG Inventory", "rice and managed-soil emissions", extracts["urls"]["ghgi"]),
        ("SRC_PHL_V22_IPCC_AFOLU", "IPCC TFI", "2019 Refinement Volume 4", "land stock-change method", extracts["urls"]["ipcc_afolu"]),
    ]:
        source_rows.append({"source_id": sid, "provider": provider, "product": product, "edition": "retained 2026-08-20", "reference_period": "2020-2053", "geography": "Philippines", "variable": variable, "source_unit": "source-specific", "exact_locator": "See hashed retained extract", "url": url, "access_date": "2026-08-20", "license": "Provider terms", "sha256": digest, "local_file": local, "notes": "Numerical facts and classifications retained locally."})
    append_csv(ledger / "SOURCES.csv", source_rows)
    append_csv(ledger / "ASSUMPTIONS.csv", [
        {"assumption_id": "ASM_PHL_V22_NO_OUTCOME_FORCING", "statement": "Observed activities, fuel shares, irrigation volumes and groundwater shares are validation benchmarks only.", "evidence_source_ids": "SRC_PHL_V22_SOURCE_CASE", "rationale": "Repository master rule."},
        {"assumption_id": "ASM_PHL_V22_COOKING_EFFICIENCY", "statement": "Household inputs convert to useful cooking energy at sourced generic end-use efficiencies; the coal label remains a disclosed charcoal proxy.", "central_value": json.dumps(COOKING_EFFICIENCY, sort_keys=True), "unit": "useful PJ/input PJ", "evidence_source_ids": "SRC_PHL_V22_WB_COOKING;SRC_PHL_V22_PSA_CPH", "rationale": "Calibrate physical conversion without prescribing fuel choice."},
        {"assumption_id": "ASM_PHL_V22_AGR_HEAT_IAR", "statement": "Agriculture oil and gas heat use the existing sectoral 89% convention; direct electric heat uses unity input.", "central_value": json.dumps(AGRICULTURE_HEAT_IAR, sort_keys=True), "unit": "input PJ/useful PJ", "evidence_source_ids": "SRC_PHL_V22_SOURCE_CASE", "rationale": "Close free-energy routes consistently; electric unity is a disclosed judgement call, not an observed-share target."},
        {"assumption_id": "ASM_PHL_V22_DAYTYPE_COLLAPSE", "statement": "Remove the redundant wind daytype by summing YearSplit and SDP and taking YearSplit-weighted CF.", "evidence_source_ids": "SRC_PHL_V22_SOURCE_CASE", "rationale": "Lossless aggregation of an otherwise degenerate dimension."},
        {"assumption_id": "ASM_PHL_V22_AFOLU_POSTSOLVE", "statement": "Rice methane, managed-soil N2O and partial land-stock change are disclosed post-solve from endogenous land activity; nothing is enforced in the LP.", "evidence_source_ids": "SRC_PHL_V22_GHGI;SRC_PHL_V22_IPCC_AFOLU", "rationale": "Complete the represented crop/land account without adding modes, constraints, prices or caps."},
    ])
    append_csv(ledger / "CALCULATIONS.csv", [
        {"calculation_id": "CALC_PHL_V22_COOKING_IAR", "formula": "IAR=1/end-use efficiency", "source_ids": "SRC_PHL_V22_WB_COOKING", "assumption_ids": "ASM_PHL_V22_COOKING_EFFICIENCY", "input_values": json.dumps(COOKING_EFFICIENCY, sort_keys=True), "input_units": "fraction", "output_value": json.dumps({k: 1/v for k, v in COOKING_EFFICIENCY.items()}, sort_keys=True), "output_unit": "PJ/PJ", "script_path": "scripts/build_philippines_v22_integrated_repair.py", "script_version": "r8"},
        {"calculation_id": "CALC_PHL_V22_AGR_HEAT_IAR", "formula": "oil/gas IAR inherits existing agriculture coal/biomass coefficient; electricity IAR=1", "source_ids": "SRC_PHL_V22_SOURCE_CASE", "assumption_ids": "ASM_PHL_V22_AGR_HEAT_IAR", "input_values": "1.123595506;1.0", "input_units": "PJ/PJ", "output_value": json.dumps(AGRICULTURE_HEAT_IAR, sort_keys=True), "output_unit": "PJ/PJ", "script_path": "scripts/build_philippines_v22_integrated_repair.py", "script_version": "r8"},
        {"calculation_id": "CALC_PHL_V22_DOE_AFF_PJ", "formula": "438.8 ktoe * 0.041868 PJ/ktoe", "source_ids": "SRC_PHL_V22_DOE_2024_AFF", "input_values": "438.8;0.041868", "input_units": "ktoe;PJ/ktoe", "output_value": AGRICULTURE_ENERGY_2024_PJ, "output_unit": "PJ", "script_path": "scripts/build_philippines_v22_integrated_repair.py", "script_version": "r8", "notes": "Benchmark only."},
        {"calculation_id": "CALC_PHL_V22_RICE_SOIL", "formula": "solved crop activity multiplied by inventory-derived rice and managed-soil factors", "source_ids": "SRC_PHL_V22_GHGI;SRC_PHL_V22_SOURCE_CASE", "assumption_ids": "ASM_PHL_V22_AFOLU_POSTSOLVE", "input_values": "26.985;6.875;2.277", "input_units": "MtCO2e", "output_value": f"rice={RICE_CH4_FACTOR};soil={MANAGED_SOIL_FACTOR}", "output_unit": "MtCO2e/model land unit", "script_path": "scripts/run_philippines_v22_integrated_repair.py", "script_version": "r8"},
    ])
    maps = [
        {"map_id": "MAP_PHL_V22_COOKING", "model_file": "RYTCM.json", "parameter": "IAR", "entity": ";".join(COOKING_EFFICIENCY), "mode": "1", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "CALC_PHL_V22_COOKING_IAR", "model_unit": "PJ/PJ", "evidence_ids": "CALC_PHL_V22_COOKING_IAR", "evidence_type": "derived physical parameter"},
        {"map_id": "MAP_PHL_V22_AGR_HEAT", "model_file": "genData.json;RYTCM.json", "parameter": "IAR membership;IAR", "entity": ";".join(AGRICULTURE_HEAT_IAR), "mode": "1", "scenario": "SC_0 with inheritance", "years": "2020-2053", "value_or_expression": "CALC_PHL_V22_AGR_HEAT_IAR", "model_unit": "PJ/PJ", "evidence_ids": "CALC_PHL_V22_AGR_HEAT_IAR;ASM_PHL_V22_AGR_HEAT_IAR", "evidence_type": "internal convention and disclosed judgement"},
        {"map_id": "MAP_PHL_V22_DAYTYPE", "model_file": "genData.json;RYTs.json;RYCTs.json;RYTTs.json", "parameter": "DAYTYPE;TIMESLICE;YS;SDP;CF", "entity": REDUNDANT_DAYTYPE_ID, "scenario": "all", "years": "2020-2053", "value_or_expression": "YS'=YS_lo+YS_hi; SDP'=SDP_lo+SDP_hi; CF'=YS-weighted mean", "model_unit": "mixed", "evidence_ids": "ASM_PHL_V22_DAYTYPE_COLLAPSE", "evidence_type": "lossless structural aggregation"},
        {"map_id": "MAP_PHL_V22_AFOLU_POSTSOLVE", "model_file": "res/<run>/afolu_postsolve.csv", "parameter": "published accounting", "entity": ";".join(crop_names), "mode": "annual", "scenario": "each validated run", "years": "2020-2053", "value_or_expression": "endogenous crop/land activity times documented factors", "model_unit": "MtCO2e/year", "evidence_ids": "CALC_PHL_V22_RICE_SOIL;ASM_PHL_V22_AFOLU_POSTSOLVE", "evidence_type": "post-solve disclosure"},
    ]
    append_csv(ledger / "MODEL_MAP.csv", maps)
    append_csv(ledger / "GAPS.csv", [
        {"item": "AQUASTAT irrigation-boundary mismatch", "why_absent": "The benchmark is net crop requirement while model source activity is gross withdrawal and modeled delivery applies losses.", "upgrade_source": "Reconcile NIA diversions, irrigated area, crop calendars, conveyance, application and return flows.", "priority": "high", "notes": "No demand or activity equality is added."},
        {"item": "Groundwater infrastructure and source split", "why_absent": "Observed national source share is not a physical sectoral capacity; adequate stocks, safe yields and pumping-cost evidence are unavailable.", "upgrade_source": "NWRB permits, aquifer safe yields, pumping depths and infrastructure stocks by service area.", "priority": "high", "notes": "Zero groundwater is disclosed, not repaired with a fixed share."},
        {"item": "Livestock climate scope", "why_absent": "No physical livestock stock, product, feed or manure activity exists in the model.", "upgrade_source": "Add a traceable physical livestock sector before emissions accounting.", "priority": "high", "notes": "Do not claim national-agriculture completeness."},
        {"item": "Dedicated charcoal chain", "why_absent": "Household coal is only a disclosed charcoal proxy upstream of an undifferentiated coal commodity.", "upgrade_source": "Add charcoal production, price and trade objects.", "priority": "high", "notes": "Turnover remains endogenous."},
        {"item": "Agriculture heat fuel-mix validation", "why_absent": "Correct input costs may reveal distorted relative fuel economics; DOE 2024 energy and electricity share are benchmarks, not constraints.", "upgrade_source": "Technology-specific agriculture heat stock, lifetime, fuel price and process evidence.", "priority": "high", "notes": "No fuel-share anchoring is permitted."},
        {"item": "Partial land carbon pools", "why_absent": "Post-solve screen omits soil, deadwood, litter and harvested wood products.", "upgrade_source": "Philippine land-transition matrix and inventory carbon pools.", "priority": "high", "notes": "Reported as partial rather than complete FOLU."},
    ])
    append_csv(ledger / "CHANGES.csv", [{"change_id": "CHG_PHL_V22_TRANSITION_SCOPE_R8_20260820", "date": str(date(2026, 8, 20)), "class": "B", "description": "Narrow candidate: physical cooking and agriculture-heat input ratios, lossless redundant-daytype removal, and non-forcing post-solve crop/land climate publication.", "model_objects": "genData.json;RYTCM.json;RYTs.json;RYSeDt.json;RYCTs.json;RYTTs.json", "evidence_path": "calculation_notes/MODEL_FIXES_TRANSITION_SCOPE_ONLY_V22_2026-08-20.md", "map_rows_affected": ";".join(x["map_id"] for x in maps), "resolve_status": "candidate_pending_gate_and_all_scenario_solves", "author": "Codex", "commit": "", "notes": "No activity, share, dispatch, irrigated-area or groundwater-share target; no new UDC."}])
    notes = ledger / "calculation_notes" / "MODEL_FIXES_TRANSITION_SCOPE_ONLY_V22_2026-08-20.md"
    notes.write_text("""# Philippines v22 transition and scope candidate r8

This disposable candidate is intentionally narrow. It changes physical input conversion for household cooking; adds the three missing agriculture-heat input commodity memberships and ratios; collapses the redundant wind daytype losslessly; and publishes crop/land climate accounting after a successful solve. It does not contain the wider r7 biofuel, power, reliability, cooling, T&D, eligibility-date, or groundwater-pumping changes.

Observed cooking shares and the DOE 2024 agriculture/forestry/fishery total (438.8 ktoe, 18.37 PJ) and electricity share (65.6%) are validation benchmarks only. No activity or share is fixed. Oil and gas agriculture heat inherit the existing sector coefficient 1.123595506; direct electric heat uses 1.0 as a disclosed judgement because no heat-pump service is represented.

AQUASTAT's 33.28 km3 net irrigation requirement is not comparable to gross model withdrawal or loss-adjusted delivery and is not enforced. Groundwater remains unqualified pending source-specific infrastructure, safe-yield and pumping-cost data. Livestock is excluded because the model has no physical livestock sector; therefore national-agriculture climate completeness is not claimed.

Required qualification order: deterministic equation/data gate; application generation and preprocessing; GLPK matrix check; an optimal BASE solve; then optimal COAL_PHASEOUT, RE and EV solves. Nothing may be promoted unless all requested runs solve successfully and the promoted source and regenerated input are identical to the solved candidate.
""", encoding="utf-8")
    return {"ledger_snapshot": str(evidence), "ledger_snapshot_sha256": digest}


def build(target: Path):
    from Classes.Case.UpdateCaseClass import UpdateCase
    from Classes.Base import Config

    if target.exists():
        raise FileExistsError(f"candidate exists: {target}")
    if not SOURCE.is_dir() or not LEDGER_BASE.is_dir():
        raise FileNotFoundError("source case or cumulative ledger base is missing")
    source_hashes = {p.name: sha256(p) for p in SOURCE.glob("*.json")}
    shutil.copytree(SOURCE, target, ignore=shutil.ignore_patterns("res", "data_sources", ".DS_Store"))
    gen = read_json(target / "genData.json")
    gen["osy-casename"] = "Philippines_v22"
    gen["osy-date"] = "2026-08-20"
    crop_names = mutate_structure(gen)
    Config.DATA_STORAGE = STORAGE
    UpdateCase(target.name, gen).updateCase()
    write_json(target / "genData.json", gen)
    overlay_parameters(target, crop_names)
    ledger = (write_scope_only_ledger(target, crop_names, source_hashes)
              if SCOPE_ONLY else write_evidence_and_ledger(target, crop_names, source_hashes))
    manifest = {
        "schema": "philippines-v22-transition-scope-build-v1" if SCOPE_ONLY else "philippines-v22-integrated-repair-build-v1",
        "source_case": str(SOURCE),
        "candidate_case": str(target),
        "source_hashes": source_hashes,
        "candidate_hashes": {p.name: sha256(p) for p in target.glob("*.json")},
        "changed_source_files": sorted(p.name for p in target.glob("*.json") if source_hashes.get(p.name) != sha256(p)),
        "optimizer_runs": 0,
        "required_next_step": "Run deterministic design gate; do not generate or solve before it passes.",
        **ledger,
    }
    write_json(target / "documentation" / "integrated_repair_v22_build_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()
    build(args.target.resolve())


if __name__ == "__main__":
    main()
