#!/usr/bin/env python3
"""Read-only source inventory for the Philippines v23 Package 1 design."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


YEARS = tuple(str(y) for y in range(2020, 2054))
BASE = "SC_0"


def load(case: Path, name: str):
    return json.loads((case / name).read_text(encoding="utf-8"))


def row_for(table, key, tech_id, **coordinates):
    rows = [
        row for row in table[key][BASE]
        if row.get("TechId") == tech_id
        and all(row.get(name) == value for name, value in coordinates.items())
    ]
    return rows


def series_summary(rows):
    if not rows:
        return None
    result = []
    for row in rows:
        values = [row.get(year) for year in YEARS]
        changes = {}
        previous = object()
        for year, value in zip(YEARS, values):
            if value != previous:
                changes[year] = value
                previous = value
        result.append({
            "coordinates": {k: v for k, v in row.items() if k not in YEARS},
            "changes": changes,
        })
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    case = args.case.resolve()

    gen = load(case, "genData.json")
    ryt = load(case, "RYT.json")
    rytcm = load(case, "RYTCM.json")
    rytt = load(case, "RYTTs.json")
    ryct = load(case, "RYCTs.json")
    ryc = load(case, "RYC.json")
    tech_by_name = {row["Tech"]: row for row in gen["osy-tech"]}
    comm_by_id = {row["CommId"]: row["Comm"] for row in gen["osy-comm"]}
    ts_by_id = {row["TsId"]: row for row in gen["osy-ts"]}

    names = sorted({
        name for name in tech_by_name
        if any(token in name for token in (
            "BIOF", "COOK_COAL", "POW_TD", "POW_PP_SPV", "_CCS", "GH2_COAL",
            "AGR_HEAT", "POW_CHP_", "POW_GEO", "POW_PP_HY", "POW_PP_NGCC",
            "POW_PP_COAL", "POW_PP_NU", "POW_PP_WON", "POW_PP_WOF",
        ))
    })
    technologies = {}
    for name in names:
        tech = tech_by_name[name]
        tid = tech["TechId"]
        technologies[name] = {
            "id": tid,
            "description": tech["Desc"],
            "inputs": [comm_by_id[x] for x in tech.get("IAR", [])],
            "outputs": [comm_by_id[x] for x in tech.get("OAR", [])],
            "RC": series_summary(row_for(ryt, "RC", tid)),
            "TAMaxCI": series_summary(row_for(ryt, "TAMaxCI", tid)),
            "TAU": series_summary(row_for(ryt, "TAU", tid)),
            "AF": series_summary(row_for(ryt, "AF", tid)),
            "IAR": series_summary(row_for(rytcm, "IAR", tid)),
            "OAR": series_summary(row_for(rytcm, "OAR", tid)),
        }

    final_demands = {}
    for key in ("SAD", "AAD"):
        for row in ryc[key][BASE]:
            if any(row.get(year) not in (None, 0, 0.0) for year in YEARS):
                final_demands.setdefault(comm_by_id[row["CommId"]], {})[key] = series_summary([row])

    profiles = {}
    for row in ryct["SDP"][BASE]:
        comm = comm_by_id[row["CommId"]]
        if comm in final_demands:
            profiles.setdefault(comm, {})[ts_by_id[row["TsId"]]["Ts"]] = row["2020"]

    solar = {}
    solar_id = tech_by_name["PHL_POW_PP_SPV"]["TechId"]
    for row in rytt["CF"][BASE]:
        if row["TechId"] == solar_id:
            ts = ts_by_id[row["TsId"]]
            solar[str(ts["Ts"])] = {
                "season": ts["SE"], "daytype": ts["DT"],
                "bracket": ts["DTB"], "cf_2020": row["2020"],
            }

    output = {
        "case": str(case),
        "identity": {key: gen[key] for key in ("osy-version", "osy-casename", "osy-date")},
        "technologies": technologies,
        "final_demands": final_demands,
        "profiles_2020": profiles,
        "solar_cf_2020": solar,
    }
    text = json.dumps(output, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
