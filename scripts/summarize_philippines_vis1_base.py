#!/usr/bin/env python3
"""Summarize and audit the solved Philippines vIS1 BASE against sealed v36."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import build_philippines_vis1 as build


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "WebAPP/DataStorage/.Philippines_vIS1-candidate-20260828"
RUN = CASE / "res/BASE_VIS1_ISLAND_POWER"
BASE = ROOT / "WebAPP/DataStorage/Philippines_v36/res/BASE_V36_POWER_GAS_HISTORY"
YEARS = build.YEARS
CHECK_YEARS = ("2020", "2024", "2030", "2040", "2050", "2053")


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream: return list(csv.DictReader(stream))


def keyed(path: Path, keys: tuple[str, ...], value: str) -> dict[tuple[str, ...], float]:
    out = defaultdict(float)
    for row in rows(path): out[tuple(row[k] for k in keys)] += float(row[value])
    return dict(out)


def main() -> None:
    csvdir, basecsv = RUN / "csv", BASE / "csv"
    activity = keyed(csvdir / "TotalAnnualTechnologyActivityByMode.csv", ("t", "y"), "TotalAnnualTechnologyActivityByMode")
    activity_mode = keyed(csvdir / "TotalAnnualTechnologyActivityByMode.csv", ("t", "m", "y"), "TotalAnnualTechnologyActivityByMode")
    base_activity = keyed(basecsv / "TotalAnnualTechnologyActivityByMode.csv", ("t", "y"), "TotalAnnualTechnologyActivityByMode")
    capacity = keyed(csvdir / "TotalCapacityAnnual.csv", ("t", "y"), "TotalCapacityAnnual")
    new_capacity = keyed(csvdir / "NewCapacity.csv", ("t", "y"), "NewCapacity")
    production = keyed(csvdir / "ProductionByTechnologyByMode.csv", ("f", "t", "m", "y", "l"), "ProductionByTechnologyByMode")
    use = keyed(csvdir / "UseByTechnologyByMode.csv", ("f", "t", "m", "y", "l"), "UseByTechnologyByMode")
    gen = json.loads((CASE / "genData.json").read_text())
    ids = {r["Tech"]: r["TechId"] for r in gen["osy-tech"]}
    rytcn = json.loads((CASE / "RYTCn.json").read_text())
    rycn = json.loads((CASE / "RYCn.json").read_text())
    constraints = {r["Con"]: r for r in gen["osy-constraints"]}

    def one(table: list[dict], **coords: object) -> dict:
        found = [r for r in table if all(r.get(k) == v for k, v in coords.items())]
        if len(found) != 1: raise RuntimeError((coords, len(found)))
        return found[0]

    # Objective/runtime/matrix.
    record = json.loads((RUN / "optimization_record.json").read_text())
    matrix = json.loads((RUN / "generation_matrix_report.json").read_text())
    cbc_log = (RUN / "cbc.log").read_text(errors="replace")
    wall = re.search(r"Wallclock seconds\):\s+([0-9.]+)", cbc_log)
    cbc_wall = float(wall.group(1)) if wall else None

    # Node generation and sales.
    generation_by_node = {y: {n: defaultdict(float) for n in build.NODES} for y in YEARS}
    category = {
        "PHL_POW_CHP_NG_OLD": "gas", "PHL_POW_PP_NGCC": "gas", "PHL_POW_PP_NGCC_CCS": "gas_ccs",
        "PHL_POW_CHP_OIL_OLD": "oil", "PHL_POW_CHP_COAL_OLD": "coal_old", "PHL_POW_PP_COAL": "coal_new",
        "PHL_POW_PP_COAL_CCS": "coal_ccs", "PHL_POW_GEO_OLD": "geothermal", "PHL_POW_PP_HY_LA": "hydro",
        "PHL_POW_PP_SPV": "solar", "PHL_POW_PP_WON": "wind_onshore", "PHL_POW_PP_WOF": "wind_offshore",
        "PHL_POW_CHP_BIOM_OLD": "biomass_old", "PHL_POW_CHP_BIOM_FIT_OLD": "biomass_fit",
        "PHL_POW_PP_BIOM_CCS": "biomass_ccs", "PHL_POW_PP_NU": "nuclear", "PHL_POW_PP_NUSMR": "nuclear_smr",
        "PHL_POW_PP_H2": "hydrogen",
    }
    for parent in build.GENERATION:
        for node in build.NODES:
            name = f"{parent}_{node}"
            for y in YEARS: generation_by_node[y][node][category[parent]] += activity.get((name, y), 0.0)

    sales = {y: {n: activity.get((f"PHL_POW_TD_{n}", y), 0.0) for n in build.NODES} for y in YEARS}
    links = {}
    for key, spec in json.loads(build.INPUT.read_text())["interconnectors"].items():
        name = f"PHL_POW_INT_{key}"
        links[key] = {}
        for y in YEARS:
            forward = activity_mode.get((name, "1", y), 0.0)
            reverse = activity_mode.get((name, "2", y), 0.0)
            links[key][y] = {
                f"{spec['from']}_to_{spec['to']}_sent_pj": forward,
                f"{spec['to']}_to_{spec['from']}_sent_pj": reverse,
                "net_forward_delivered_pj": .97 * (forward - reverse),
            }

    # Reconstruct UDC bodies; exported UDC CSV values are duals.
    udc_residuals = {}
    for cname, con in constraints.items():
        if not (cname.startswith("PHL_LOAD_") or cname.startswith("PHL_POW_RESERVE_MARGIN_")): continue
        udc_residuals[cname] = {}
        constant = one(rycn["UCC"]["SC_0"], ConId=con["ConId"])
        for y in YEARS:
            body = 0.0
            for tid in con["CM"]:
                tname = one(gen["osy-tech"], TechId=tid)["Tech"]
                cam = one(rytcn["CAM"]["SC_0"], TechId=tid, ConId=con["ConId"])
                ccm = one(rytcn["CCM"]["SC_0"], TechId=tid, ConId=con["ConId"])
                cncm = one(rytcn["CNCM"]["SC_0"], TechId=tid, ConId=con["ConId"])
                body += float(cam[y]) * activity.get((tname, y), 0.0)
                body += float(ccm[y]) * capacity.get((tname, y), 0.0)
                body += float(cncm[y]) * new_capacity.get((tname, y), 0.0)
            udc_residuals[cname][y] = body - float(constant[y])

    equality_max = max(abs(v) for k, ys in udc_residuals.items() if k.startswith("PHL_LOAD_") for v in ys.values())
    inequality_max_violation = max(max(0.0, v) for k, ys in udc_residuals.items() if k.startswith("PHL_POW_RESERVE") for v in ys.values())
    binding_reserve = {n: [y for y, v in udc_residuals[f"PHL_POW_RESERVE_MARGIN_{n}"].items() if abs(v) < 1e-5] for n in build.NODES}

    # Annual/timeslice commodity balances at every new electricity bus.
    balance_max = 0.0
    balance_worst = None
    node_fuels = [f"PHL_POW_ELE_{n}" for n in build.NODES] + [f"PHL_POW_ELE1_{n}" for n in build.NODES]
    prod_balance = defaultdict(float)
    use_balance = defaultdict(float)
    for (f, t, m, y, l), value in production.items():
        if f in node_fuels: prod_balance[(f, y, l)] += value
    for (f, t, m, y, l), value in use.items():
        if f in node_fuels: use_balance[(f, y, l)] += value
    for fuel in node_fuels:
        coordinates = {(y, l) for f, y, l in prod_balance if f == fuel} | {(y, l) for f, y, l in use_balance if f == fuel}
        for y, l in coordinates:
            p = prod_balance.get((fuel, y, l), 0.0)
            u = use_balance.get((fuel, y, l), 0.0)
            residual = p - u
            if abs(residual) > balance_max:
                balance_max, balance_worst = abs(residual), [fuel, y, l, p, u, residual]

    # Split generation sum compared with the national v36 technology.
    national_generation_delta = {}
    for parent in build.GENERATION:
        national_generation_delta[parent] = {}
        for y in CHECK_YEARS:
            candidate = sum(activity.get((f"{parent}_{n}", y), 0.0) for n in build.NODES)
            control = base_activity.get((parent, y), 0.0)
            national_generation_delta[parent][y] = {"v36_pj": control, "vIS1_pj": candidate, "delta_pj": candidate-control}

    offgrid_delta = {}
    for name in ("PHL_POW_CHP_OIL_OFFGRID", "PHL_POW_RE_OFFGRID"):
        offgrid_delta[name] = {y: activity.get((name, y), 0.0) - base_activity.get((name, y), 0.0) for y in CHECK_YEARS}

    # Largest changes outside explicitly spatialized technologies.
    spatial_prefixes = tuple(build.GENERATION) + ("PHL_POW_TD", "PHL_POW_INT_", "PHL_PRO_DEL_", *build.DIRECT_GRID, *build.COOLING)
    unchanged_names = set(t for t, y in base_activity) & set(t for t, y in activity)
    changes = []
    for name in unchanged_names:
        if name.startswith(spatial_prefixes): continue
        absolute = sum(abs(activity.get((name, y), 0.0) - base_activity.get((name, y), 0.0)) for y in YEARS)
        if absolute: changes.append({"technology": name, "sum_abs_activity_delta_pj": absolute})
    changes.sort(key=lambda x: x["sum_abs_activity_delta_pj"], reverse=True)

    new_builds = []
    for (name, y), value in new_capacity.items():
        if value > 1e-7 and (any(name.endswith("_" + n) for n in build.NODES) or name.startswith("PHL_POW_INT_")):
            new_builds.append({"technology": name, "year": y, "gw": value})
    new_builds.sort(key=lambda x: (x["year"], x["technology"]))

    report = {
        "status": "BASE_optimal_assessment_complete",
        "objective": record["objective"], "objective_change_percent_vs_v36": record["objective_change_percent"],
        "cbc_wall_seconds": cbc_wall, "v36_wall_seconds": 68.15735912499076,
        "cbc_wall_ratio_vs_v36": cbc_wall / 68.15735912499076 if cbc_wall else None,
        "matrix": matrix["matrix_dimensions"], "matrix_ratios_vs_v36": matrix["matrix_ratios"],
        "electricity_balance_max_abs_pj": balance_max, "electricity_balance_worst": balance_worst,
        "load_equality_max_abs_residual_pj": equality_max,
        "reserve_max_positive_violation_gw": inequality_max_violation,
        "binding_reserve_years": binding_reserve,
        "node_sales_pj": {y: sales[y] for y in CHECK_YEARS},
        "node_generation_pj": {y: {n: dict(generation_by_node[y][n]) for n in build.NODES} for y in CHECK_YEARS},
        "interconnector_flows": {k: {y: values[y] for y in CHECK_YEARS} for k, values in links.items()},
        "new_spatial_capacity": new_builds,
        "national_generation_delta": national_generation_delta,
        "offgrid_activity_delta_pj": offgrid_delta,
        "largest_nonspatial_activity_changes": changes[:20],
        "policy_generation_interrupted": True,
        "optimizer_runs": 1,
    }
    out = CASE / "documentation/base_results_assessment_vIS1.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
