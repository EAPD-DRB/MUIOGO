#!/usr/bin/env python3
"""Compare sectoral BASE results between Philippines v36 and vIS1."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V36 = ROOT / "WebAPP/DataStorage/Philippines_v36/res/BASE_V36_POWER_GAS_HISTORY/csv"
VIS1 = ROOT / "WebAPP/DataStorage/.Philippines_vIS1-candidate-20260828/res/BASE_VIS1_ISLAND_POWER/csv"
OUT = ROOT / "WebAPP/DataStorage/.Philippines_vIS1-candidate-20260828/documentation/sector_comparison_v36_vIS1.json"
YEARS = [str(y) for y in range(2020, 2054)]
REPORT_YEARS = ("2020", "2024", "2030", "2040", "2050", "2053")
SECTORS = ("agriculture", "fisheries", "industry", "transport", "services", "households", "power", "land", "water")


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream: return list(csv.DictReader(stream))


def sector(technology: str) -> str | None:
    if technology.startswith(("PHL_AGR_", "DEMAGR")): return "agriculture"
    if technology.startswith("PHL_FSH_"): return "fisheries"
    if technology.startswith("PHL_INDU_"): return "industry"
    if technology.startswith("PHL_TRA_"): return "transport"
    if technology.startswith(("PHL_SER_", "PHL_DEM_PUB_")): return "services"
    if technology.startswith("PHL_HOU_"): return "households"
    if technology.startswith(("PHL_POW_", "PHL_DEM_PWR_")): return "power"
    if technology.startswith(("LND", "MINLND", "MINPRC")): return "land"
    if technology == "ENV_WATER": return "water"
    return None


def carrier(commodity: str) -> str | None:
    if "_ELE" in commodity and not commodity.endswith("ELEF"): return "electricity"
    if commodity.startswith("PHL_PRO_OIL"): return "oil"
    if commodity.startswith("PHL_PRO_NG"): return "natural_gas"
    if commodity.startswith("PHL_PRO_COAL"): return "coal"
    if commodity.startswith(("PHL_PRO_BIOM", "PHL_PRO_BIOF")): return "biomass"
    if commodity == "PHL_PRO_LIQ": return "liquid_fuel"
    if commodity == "PHL_POW_H2": return "hydrogen"
    return None


def aggregate(directory: Path, vis1: bool) -> dict:
    use = defaultdict(float)
    for row in read(directory / "UseByTechnologyByMode.csv"):
        sec, fuel = sector(row["t"]), carrier(row["f"])
        if sec and fuel: use[(sec, fuel, row["y"])] += float(row["UseByTechnologyByMode"])
    emissions = defaultdict(float)
    system_emissions = defaultdict(float)
    for row in read(directory / "AnnualTechnologyEmission.csv"):
        system_emissions[(row["e"], row["y"])] += float(row["AnnualTechnologyEmission"])
        sec = sector(row["t"])
        if sec: emissions[(sec, row["e"], row["y"])] += float(row["AnnualTechnologyEmission"])
    activity = defaultdict(float)
    for row in read(directory / "TotalAnnualTechnologyActivityByMode.csv"):
        activity[(row["t"], row["y"])] += float(row["TotalAnnualTechnologyActivityByMode"])
    delivered = defaultdict(float)
    suffix = {"agriculture": "AGR", "fisheries": "FSH", "industry": "INDU", "transport": "TRA", "services": "SER", "households": "HOU"}
    for sec, code in suffix.items():
        for y in YEARS:
            if vis1:
                delivered[(sec, y)] = sum(activity[(f"PHL_POW_TD_{code}_{n}", y)] for n in ("LUZ", "VIS", "MIN"))
            else:
                delivered[(sec, y)] = activity[(f"PHL_POW_TD_{code}", y)]
    return {"use": use, "emissions": emissions, "system_emissions": system_emissions, "activity": activity, "delivered": delivered}


def main() -> None:
    base, candidate = aggregate(V36, False), aggregate(VIS1, True)
    report = {"status": "comparison_complete", "units": {"carrier_use": "PJ", "electricity_delivery": "PJ", "CO2e": "model emission unit"}, "system_emissions": {}, "sectors": {}}
    for y in REPORT_YEARS:
        report["system_emissions"][y] = {}
        for emission in ("CO2e", "PM2_5"):
            before, after = base["system_emissions"].get((emission, y), 0.0), candidate["system_emissions"].get((emission, y), 0.0)
            report["system_emissions"][y][emission] = {"v36": before, "vIS1": after, "delta": after-before, "percent": ((after/before-1)*100 if before else None)}
    for sec in SECTORS:
        fuels = sorted({fuel for s, fuel, y in base["use"] if s == sec} | {fuel for s, fuel, y in candidate["use"] if s == sec})
        item = {"carrier_use": {}, "co2e": {}, "electricity_delivery": {}}
        for y in REPORT_YEARS:
            item["carrier_use"][y] = {}
            for fuel in fuels:
                before, after = base["use"].get((sec, fuel, y), 0.0), candidate["use"].get((sec, fuel, y), 0.0)
                item["carrier_use"][y][fuel] = {"v36": before, "vIS1": after, "delta": after-before, "percent": ((after/before-1)*100 if before else None)}
            before, after = base["emissions"].get((sec, "CO2e", y), 0.0), candidate["emissions"].get((sec, "CO2e", y), 0.0)
            item["co2e"][y] = {"v36": before, "vIS1": after, "delta": after-before, "percent": ((after/before-1)*100 if before else None)}
            if sec in ("agriculture", "fisheries", "industry", "transport", "services", "households"):
                before, after = base["delivered"][(sec, y)], candidate["delivered"][(sec, y)]
                item["electricity_delivery"][y] = {"v36": before, "vIS1": after, "delta": after-before, "percent": ((after/before-1)*100 if before else None)}
        report["sectors"][sec] = item

    # Identify the largest common-technology changes inside each sector without
    # aggregating model activities across different units.
    common = {t for t, y in base["activity"]} & {t for t, y in candidate["activity"]}
    for sec in SECTORS:
        changes = []
        for tech in common:
            if sector(tech) != sec: continue
            delta = sum(abs(candidate["activity"].get((tech, y), 0.0) - base["activity"].get((tech, y), 0.0)) for y in YEARS)
            if delta: changes.append({"technology": tech, "sum_abs_annual_activity_delta": delta})
        changes.sort(key=lambda x: x["sum_abs_annual_activity_delta"], reverse=True)
        report["sectors"][sec]["largest_common_technology_changes"] = changes[:10]
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
