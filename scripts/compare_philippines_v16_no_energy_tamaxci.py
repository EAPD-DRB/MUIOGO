#!/usr/bin/env python3
"""Compare the Philippines v16 BASE run with the no-energy-TAMaxCI run.

Both solutions are read straight from the CBC ``results.txt`` files so the two
runs are read by exactly the same parser. The script writes a JSON report and
prints a readable summary.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STORAGE = REPO / "WebAPP" / "DataStorage"

# variable name -> index labels, in the order CBC prints them
WANTED = {
    "NewCapacity": ("r", "t", "y"),
    "TotalCapacityAnnual": ("r", "t", "y"),
    "TotalTechnologyAnnualActivity": ("r", "t", "y"),
    "AnnualTechnologyEmission": ("r", "t", "e", "y"),
    "CapitalInvestment": ("r", "t", "y"),
    "AnnualFixedOperatingCost": ("r", "t", "y"),
    "AnnualVariableOperatingCost": ("r", "t", "y"),
    "DiscountedSalvageValue": ("r", "t", "y"),
    "NCC1_TotalAnnualMaxNewCapacityConstraint": ("r", "t", "y"),
}
DUAL_WANTED = {"NCC1_TotalAnnualMaxNewCapacityConstraint"}

LINE = re.compile(r"^\s*\d+\s+([A-Za-z_][\w]*)\((.*?)\)\s+(\S+)\s+(\S+)\s*$")

SECTORS = (
    ("power", "PHL_POW_"),
    ("supply", "PHL_PRO_"),
    ("transport", "PHL_TRA_"),
    ("industry", "PHL_INDU_"),
    ("services", "PHL_SER_"),
    ("households", "PHL_HOU_"),
    ("agriculture_energy", "PHL_AGR_"),
    ("fisheries_energy", "PHL_FSH_"),
    ("water", "PHL_DEM_"),
)
REPORT_YEARS = ("2020", "2025", "2030", "2040", "2053")


def sector_of(tech: str) -> str:
    for name, prefix in SECTORS:
        if tech.startswith(prefix):
            return name
    if tech.startswith(("LND", "MINLND", "PHL_LND", "ENV_LAND")):
        return "land"
    if tech.startswith(("MINPRC", "PHL_WTR", "DEMAGR", "ENV_WATER")):
        return "water"
    return "other"


def load(results: Path) -> dict:
    values: dict[str, dict[tuple, float]] = {name: {} for name in WANTED}
    duals: dict[str, dict[tuple, float]] = {name: {} for name in DUAL_WANTED}
    status = ""
    with results.open() as stream:
        status = stream.readline().strip()
        for line in stream:
            match = LINE.match(line)
            if match is None:
                continue
            name, keys, primal, dual = match.groups()
            if name not in WANTED:
                continue
            key = tuple(keys.split(","))
            values[name][key] = float(primal)
            if name in DUAL_WANTED:
                duals[name][key] = float(dual)
    objective = re.search(r"objective value\s*([-+0-9.eE]+)", status)
    return {
        "status": status,
        "objective": float(objective.group(1)) if objective else None,
        "values": values,
        "duals": duals,
    }


def by_year(series: dict[tuple, float], tech_index: int = 1, year_index: int = -1) -> dict:
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for key, value in series.items():
        out[key[tech_index]][key[year_index]] = value
    return out


def sector_totals(series: dict[tuple, float]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (_r, tech, year), value in series.items():
        out[sector_of(tech)][year] += value
    return {k: dict(v) for k, v in out.items()}


def emission_totals(series: dict[tuple, float]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (_r, _tech, emission, year), value in series.items():
        out[emission][year] += value
    return {k: dict(v) for k, v in out.items()}


def emission_by_tech(series: dict[tuple, float], emission: str) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for (_r, tech, emis, year), value in series.items():
        if emis == emission:
            out[tech][year] = value
    return dict(out)


def top_changes(base: dict, cand: dict, years: tuple[str, ...], limit: int, floor: float):
    rows = []
    keys = set(base) | set(cand)
    for key in keys:
        b = base.get(key, {})
        c = cand.get(key, {})
        delta = {y: c.get(y, 0.0) - b.get(y, 0.0) for y in years}
        magnitude = max(abs(v) for v in delta.values())
        if magnitude < floor:
            continue
        rows.append(
            {
                "tech": key,
                "sector": sector_of(key),
                "max_abs_delta": magnitude,
                "base": {y: b.get(y, 0.0) for y in years},
                "candidate": {y: c.get(y, 0.0) for y in years},
                "delta": delta,
            }
        )
    rows.sort(key=lambda row: -row["max_abs_delta"])
    return rows[:limit]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base",
        type=Path,
        default=STORAGE / "Philippines_v16" / "res" / "BASE_V15" / "results.txt",
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        default=STORAGE
        / ".Philippines_v16-no-energy-tamaxci"
        / "res"
        / "BASE_V15"
        / "results.txt",
    )
    parser.add_argument("--manifest", type=Path,
                        default=STORAGE / ".Philippines_v16-no-energy-tamaxci"
                        / "no_energy_tamaxci_manifest.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    cleared = {item["tech"] for item in manifest["cleared"]}

    base = load(args.base)
    cand = load(args.candidate)

    years = REPORT_YEARS
    bv, cv = base["values"], cand["values"]

    # Which of the removed bounds were actually binding in BASE?
    binding = defaultdict(list)
    for key, dual in base["duals"]["NCC1_TotalAnnualMaxNewCapacityConstraint"].items():
        if dual != 0.0:
            binding[key[1]].append(key[2])
    binding_energy = {t: sorted(ys) for t, ys in binding.items() if t in cleared}

    # New capacity built at all in each run (any year)
    def built(series):
        out = defaultdict(float)
        for (_r, tech, _y), value in series.items():
            out[tech] += value
        return out

    base_built, cand_built = built(bv["NewCapacity"]), built(cv["NewCapacity"])

    def total_cost(name: str) -> dict[str, float]:
        out = defaultdict(float)
        for (_r, _t, year), value in bv[name].items():
            out[year] += value
        return dict(out)

    report = {
        "base": {"results": str(args.base), "status": base["status"], "objective": base["objective"]},
        "candidate": {
            "results": str(args.candidate),
            "status": cand["status"],
            "objective": cand["objective"],
        },
        "objective_delta": (cand["objective"] or 0) - (base["objective"] or 0),
        "objective_delta_pct": 100
        * ((cand["objective"] or 0) - (base["objective"] or 0))
        / (base["objective"] or 1),
        "bounds_removed": len(cleared),
        "bounds_binding_in_base": {
            "technologies": len(binding_energy),
            "tech_year_pairs": sum(len(v) for v in binding_energy.values()),
            "detail": {t: {"years": ys, "count": len(ys)} for t, ys in sorted(binding_energy.items())},
        },
        "report_years": list(years),
        "capacity": {
            "sector_totals_base": sector_totals(bv["TotalCapacityAnnual"]),
            "sector_totals_candidate": sector_totals(cv["TotalCapacityAnnual"]),
            "top_changes": top_changes(
                by_year(bv["TotalCapacityAnnual"]), by_year(cv["TotalCapacityAnnual"]),
                years, 30, 1e-4,
            ),
        },
        "new_capacity_model_period": {
            "top_changes": sorted(
                (
                    {
                        "tech": t,
                        "sector": sector_of(t),
                        "base": base_built.get(t, 0.0),
                        "candidate": cand_built.get(t, 0.0),
                        "delta": cand_built.get(t, 0.0) - base_built.get(t, 0.0),
                    }
                    for t in set(base_built) | set(cand_built)
                    if abs(cand_built.get(t, 0.0) - base_built.get(t, 0.0)) > 1e-6
                ),
                key=lambda row: -abs(row["delta"]),
            )[:40]
        },
        "activity": {
            "sector_totals_base": sector_totals(bv["TotalTechnologyAnnualActivity"]),
            "sector_totals_candidate": sector_totals(cv["TotalTechnologyAnnualActivity"]),
            "top_changes": top_changes(
                by_year(bv["TotalTechnologyAnnualActivity"]),
                by_year(cv["TotalTechnologyAnnualActivity"]),
                years, 40, 1e-3,
            ),
        },
        "emissions": {
            "base": emission_totals(bv["AnnualTechnologyEmission"]),
            "candidate": emission_totals(cv["AnnualTechnologyEmission"]),
            "co2e_top_changes": top_changes(
                emission_by_tech(bv["AnnualTechnologyEmission"], "CO2e"),
                emission_by_tech(cv["AnnualTechnologyEmission"], "CO2e"),
                years, 20, 1e-3,
            ),
            "pm25_top_changes": top_changes(
                emission_by_tech(bv["AnnualTechnologyEmission"], "PM2_5"),
                emission_by_tech(cv["AnnualTechnologyEmission"], "PM2_5"),
                years, 20, 1e-6,
            ),
        },
        "costs": {
            name: {
                "base": {y: sum(v for (_r, _t, yy), v in bv[name].items() if yy == y) for y in years},
                "candidate": {y: sum(v for (_r, _t, yy), v in cv[name].items() if yy == y) for y in years},
                "base_model_period": sum(bv[name].values()),
                "candidate_model_period": sum(cv[name].values()),
            }
            for name in (
                "CapitalInvestment",
                "AnnualFixedOperatingCost",
                "AnnualVariableOperatingCost",
                "DiscountedSalvageValue",
            )
        },
    }

    args.out.write_text(json.dumps(report, indent=2) + "\n")

    print(f"BASE      {base['status']}")
    print(f"CANDIDATE {cand['status']}")
    print(
        "objective  base={:,.2f}  candidate={:,.2f}  delta={:,.2f} ({:+.3f}%)".format(
            base["objective"], cand["objective"], report["objective_delta"],
            report["objective_delta_pct"],
        )
    )
    print(
        "bounds removed={}  binding in BASE: {} techs / {} tech-years".format(
            report["bounds_removed"],
            report["bounds_binding_in_base"]["technologies"],
            report["bounds_binding_in_base"]["tech_year_pairs"],
        )
    )
    print("\nemission totals")
    for emission in sorted(report["emissions"]["base"]):
        b = report["emissions"]["base"][emission]
        c = report["emissions"]["candidate"].get(emission, {})
        for year in years:
            print(
                f"  {emission:6s} {year}  base={b.get(year,0):14,.3f}  cand={c.get(year,0):14,.3f}"
                f"  delta={c.get(year,0)-b.get(year,0):+14,.3f}"
            )
    print("\ntop capacity changes")
    for row in report["capacity"]["top_changes"][:15]:
        print(
            f"  {row['tech']:26s} {row['sector']:18s} "
            + "  ".join(f"{y}:{row['delta'][y]:+11.3f}" for y in years)
        )
    print("\ntop activity changes")
    for row in report["activity"]["top_changes"][:20]:
        print(
            f"  {row['tech']:26s} {row['sector']:18s} "
            + "  ".join(f"{y}:{row['delta'][y]:+11.3f}" for y in years)
        )
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
