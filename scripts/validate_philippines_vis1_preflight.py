#!/usr/bin/env python3
"""Zero-solve equation-first and constructive-feasibility gate for Philippines vIS1.x."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import build_philippines_vis1 as build


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "WebAPP/DataStorage/Philippines_v36"
DEFAULT = ROOT / "WebAPP/DataStorage/.Philippines_vIS11-candidate-20260828"
VIS11 = ROOT / "WebAPP/DataStorage/.Philippines_vIS11-candidate-20260828"
V12_INPUT = ROOT / "scripts/data/philippines_vis1/v12_spatial_costs.json"
TOL = 1e-8


def load(case: Path, name: str) -> dict:
    return json.loads((case / name).read_text(encoding="utf-8"))


def one(rows: list[dict], **coords: object) -> dict:
    found = [r for r in rows if all(r.get(k) == v for k, v in coords.items())]
    if len(found) != 1:
        raise RuntimeError(f"Expected one row at {coords}, found {len(found)}")
    return found[0]


def close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)), abs(float(b)))


def annual_baseline_grid_use() -> dict[str, float]:
    path = BASE / "res/BASE_V36_POWER_GAS_HISTORY/csv/UseByTechnologyByMode.csv"
    result = {y: 0.0 for y in build.YEARS}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["f"] == "PHL_POW_ELE":
                result[row["y"]] += float(row["UseByTechnologyByMode"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=DEFAULT)
    args = parser.parse_args()
    case = args.case.resolve()
    inputs = json.loads(build.INPUT.read_text())
    base_gen, gen = load(BASE, "genData.json"), load(case, "genData.json")
    base_ids = {r["CommId"] for r in base_gen["osy-comm"]}
    tech = {r["Tech"]: r for r in gen["osy-tech"]}
    comm = {r["Comm"]: r for r in gen["osy-comm"]}
    ryt, rytcm, rytt, rytcn, rycn, rt = (load(case, f) for f in ("RYT.json", "RYTCM.json", "RYTTs.json", "RYTCn.json", "RYCn.json", "RT.json"))
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: object) -> None:
        checks.append({"name": name, "status": "pass" if passed else "fail", "detail": detail})

    case_identity = gen.get("osy-casename")
    is_v12 = case_identity == "Philippines_vIS1.2"
    check("case_identity", case_identity in ("Philippines_vIS1.1", "Philippines_vIS1.2"), case_identity)
    names = [r["Tech"] for r in gen["osy-tech"]]
    cnames = [r["Con"] for r in gen["osy-constraints"]]
    check("unique_structural_names", len(names) == len(set(names)) and len(cnames) == len(set(cnames)),
          {"technology_duplicates": len(names) - len(set(names)), "constraint_duplicates": len(cnames) - len(set(cnames))})

    # The data writer overlays active scenarios onto BASE. Every BASE UDC
    # constant must therefore be explicit: a null here can fall through when
    # the active policy layer is also null and must never reach LP generation.
    udc_fallthrough = []
    for row in rycn["UCC"][build.SC_BASE]:
        for year in build.YEARS:
            if row[year] is None:
                udc_fallthrough.append([row["ConId"], year])
    check("no_base_udc_constant_fallthrough_cells", not udc_fallthrough, udc_fallthrough[:20])

    # Existing final-demand values and profiles are not multiplied by new nodes.
    base_ryc, cand_ryc = load(BASE, "RYC.json"), load(case, "RYC.json")
    base_rycts, cand_rycts = load(BASE, "RYCTs.json"), load(case, "RYCTs.json")
    demand_errors = []
    for source, target in ((base_ryc, cand_ryc), (base_rycts, cand_rycts)):
        for parameter in source:
            for scenario, rows in source[parameter].items():
                for row in rows:
                    if row.get("CommId") not in base_ids:
                        continue
                    coords = {k: row[k] for k in ("CommId", "TsId") if k in row}
                    match = one(target[parameter][scenario], **coords)
                    for y in build.YEARS:
                        if row[y] != match[y]: demand_errors.append([parameter, scenario, coords, y, row[y], match[y]])
    check("national_final_demand_and_profiles_not_duplicated", not demand_errors, demand_errors[:10])

    # All split stock and investment envelopes sum exactly to the v36 control.
    conservation = []
    base_ryt = load(BASE, "RYT.json")
    base_tech = {r["Tech"]: r["TechId"] for r in base_gen["osy-tech"]}
    split_names = [*build.GENERATION, "PHL_POW_TD", *build.DIRECT_GRID]
    for name in split_names:
        for parameter in ("RC", "TAMaxC", "TAMaxCI", "TAMinC", "TAMinCI"):
            for scenario in ryt[parameter]:
                parent = one(base_ryt[parameter][scenario], TechId=base_tech[name])
                children = [one(ryt[parameter][scenario], TechId=tech[f"{name}_{n}"]["TechId"])
                            for n in build.NODES if f"{name}_{n}" in tech]
                for y in build.YEARS:
                    values = [r[y] for r in children]
                    if parent[y] is None:
                        ok = all(v is None for v in values)
                    else:
                        ok = close(sum(float(v) for v in values), float(parent[y]))
                    # vIS1.2 replaces the inherited 1,000,000-GW renewable
                    # placeholder with sourced CREZ potential; it is checked
                    # independently below rather than conserved.
                    if is_v12 and parameter == "TAMaxC" and name in ("PHL_POW_PP_SPV", "PHL_POW_PP_WON"):
                        ok = True
                    if not ok: conservation.append([name, parameter, scenario, y, parent[y], values])
    check("stock_and_investment_envelopes_split_never_duplicated", not conservation, conservation[:12])

    # No generation activity pins were introduced. Scenario coal closures remain upper bounds only.
    lower_errors = []
    for parameter in ("TAL", "TAMinC", "TAMinCI"):
        for scenario, rows in ryt[parameter].items():
            for row in rows:
                tname = one(gen["osy-tech"], TechId=row["TechId"])["Tech"]
                if any(tname.startswith(name + "_") for name in build.GENERATION):
                    for y in build.YEARS:
                        if row[y] not in (None, 0, 0.0): lower_errors.append([parameter, scenario, tname, y, row[y]])
    check("no_generation_activity_or_capacity_floor", not lower_errors, lower_errors[:10])

    # Commodity topology: each node bus has local production, local use, and only named transfers cross nodes.
    topology_errors = []
    national_gross = comm["PHL_POW_ELE"]["CommId"]
    grid_generators = [r for r in gen["osy-tech"] if any(r["Tech"].startswith(n + "_") for n in build.GENERATION)]
    if any(national_gross in r["OAR"] for r in grid_generators): topology_errors.append("grid generator still produces national gross bus")
    for node in build.NODES:
        gross = comm[f"PHL_POW_ELE_{node}"]["CommId"]
        sales = comm[f"PHL_POW_ELE1_{node}"]["CommId"]
        producers = [r["Tech"] for r in gen["osy-tech"] if gross in r["OAR"]]
        users = [r["Tech"] for r in gen["osy-tech"] if gross in r["IAR"]]
        if not producers or not users: topology_errors.append([node, "orphan", producers, users])
        for row in gen["osy-tech"]:
            touches = gross in row["IAR"] or gross in row["OAR"] or sales in row["IAR"] or sales in row["OAR"]
            if touches and any(other in row["Tech"] for other in build.NODES if other != node) and not row["Tech"].startswith("PHL_POW_INT_"):
                topology_errors.append([node, "cross-node technology", row["Tech"]])
    off = comm["PHL_POW_ELE_OFFGRID_FINAL"]["CommId"]
    connector_rows = [r for r in gen["osy-tech"] if r["Tech"].startswith("PHL_POW_INT_")]
    if any(off in r["IAR"] or off in r["OAR"] for r in connector_rows): topology_errors.append("OFF connected")
    check("node_commodity_reachability_and_off_isolation", not topology_errors, topology_errors[:20])

    # Zero-information delivery paths and node fuel aliases are absent. Fuel
    # access remains national, while the gas build envelope is Luzon-only.
    fuel_errors = [name for name in tech if name.startswith("PHL_PRO_DEL_")]
    fuel_errors += [name for name in comm if any(name == f"{fuel}_{node}" for fuel, _ in build.FUEL_COMMODITIES.values() for node in build.NODES)]
    for parent in ("PHL_POW_CHP_NG_OLD", "PHL_POW_PP_NGCC", "PHL_POW_PP_NGCC_CCS"):
        for node in ("VIS", "MIN"):
            name = f"{parent}_{node}"
            if name in tech:
                tid = tech[name]["TechId"]
                row = one(ryt["TAMaxCI"][build.SC_BASE], TechId=tid)
                if any(float(row[y]) != 0.0 for y in build.YEARS): fuel_errors.append([parent, node, "gas build enabled"])
    check("redundant_fuel_delivery_removed_and_gas_access_bounded", not fuel_errors, fuel_errors)

    # Link modes, losses, shared capacity, and MVIP commissioning.
    link_errors = []
    for key, spec in inputs["interconnectors"].items():
        row = tech[f"PHL_POW_INT_{key}"]
        tid = row["TechId"]
        rc = one(ryt["RC"][build.SC_BASE], TechId=tid)
        expected = {y: (0.44 if key == "LV" else (0.45 if int(y) >= 2023 else 0.0)) for y in build.YEARS}
        if any(not close(rc[y], expected[y]) for y in build.YEARS): link_errors.append([key, "RC"])
        total = one(ryt["TAMaxC"][build.SC_BASE], TechId=tid)
        for y in build.YEARS:
            residual = expected[y]
            ceiling = residual + (float(spec["additional_limit_gw"]) if int(y) >= int(spec["additional_from_year"]) else 0.0)
            if not close(total[y], ceiling): link_errors.append([key, "TAMaxC", y, total[y], ceiling])
        relations = [r for r in rytcm["IAR"][build.SC_BASE] + rytcm["OAR"][build.SC_BASE]
                     if r["TechId"] == tid and r["MoId"] in (1, 2)
                     and any(float(r[y] or 0.0) != 0.0 for y in build.YEARS)]
        if len(relations) != 4: link_errors.append([key, "mode_relations", len(relations)])
    check("interconnector_modes_losses_and_historical_commissioning", not link_errors, link_errors)

    # Six bundle technologies consume all three node deliveries in exact,
    # positive geographic proportions; no load-ratio UDC remains.
    share_errors = [c["Con"] for c in gen["osy-constraints"] if c["Con"].startswith("PHL_LOAD_")]
    national_sales = comm["PHL_POW_ELE1"]["CommId"]
    for tech_name, field in build.SECTOR_TD.items():
        tid = tech[tech_name]["TechId"]
        if national_sales in tech[tech_name]["IAR"]: share_errors.append([tech_name, "national sales input remains"])
        for y in build.YEARS:
            source_year = y if y in build.HISTORY else "2024"
            expected_shares = build.shares(build.history_values(inputs, source_year, "sales_gwh", field))
            actual = {}
            for node in build.NODES:
                cid = comm[f"PHL_POW_ELE1_{node}"]["CommId"]
                row = one(rytcm["IAR"][build.SC_BASE], TechId=tid, CommId=cid, MoId=1)
                actual[node] = float(row[y])
            total = sum(actual.values())
            if not close(total, 1.0) or any(not close(actual[n], expected_shares[n]) for n in build.NODES):
                share_errors.append([tech_name, y, actual, expected_shares])
    check("sector_electricity_bundles_replace_load_equalities", not share_errors, share_errors[:10])

    negative_capacity = []
    for parameter in ("RC", "TAMaxC", "TAMaxCI", "TAMinC", "TAMinCI"):
        for scenario, rows in ryt[parameter].items():
            for row in rows:
                for y in build.YEARS:
                    if row[y] is not None and float(row[y]) < 0:
                        negative_capacity.append([parameter, scenario, row["TechId"], y, row[y]])
    check("no_negative_capacity_parameters", not negative_capacity, negative_capacity[:20])

    oil_import = tech["PHL_PRO_IMP_OIL"]["TechId"]
    coal_oil_tal = one(ryt["TAL"][build.SC_COAL_PHASEOUT], TechId=oil_import)
    base_oil_tal = one(ryt["TAL"][build.SC_BASE], TechId=oil_import)
    oil_floor_errors = [[year, coal_oil_tal[year], base_oil_tal[year]] for year in build.YEARS
                        if coal_oil_tal[year] is not None or float(base_oil_tal[year]) != 0.0]
    check("coal_phaseout_oil_import_floor_removed", not oil_floor_errors, oil_floor_errors[:20])

    nuclear = next(c for c in gen["osy-constraints"] if c["Con"] == "NUCLEAR_CAPACITY_TARGET")
    nuclear_base_errors = []
    for row in rycn["UCC"][build.SC_BASE]:
        if row["ConId"] == nuclear["ConId"]:
            nuclear_base_errors.extend([y, v] for y, v in row.items() if y.isdigit() and v != 0 and v != 0.0)
    for parameter in ("CAM", "CCM"):
        for row in rytcn[parameter][build.SC_BASE]:
            if row.get("ConId") == nuclear["ConId"]:
                nuclear_base_errors.extend([parameter, row["TechId"], y, v] for y, v in row.items()
                                           if y.isdigit() and v != 0 and v != 0.0)
    check("base_nuclear_policy_equality_explicitly_neutral", not nuclear_base_errors,
          nuclear_base_errors[:10])

    if is_v12:
        spatial = json.loads(V12_INPUT.read_text(encoding="utf-8"))
        parent_gen = load(VIS11, "genData.json")
        parent_ryt = load(VIS11, "RYT.json")
        parent_ids = {r["Tech"]: r["TechId"] for r in parent_gen["osy-tech"]}
        removed_errors = []
        expected_removed = spatial["structural_cleanup"]["removed_zero_reachability_node_technologies"]
        for name in expected_removed:
            if name in tech: removed_errors.append([name, "still present"])
            tid = parent_ids[name]
            for parameter in ("RC", "TAMaxC", "TAMaxCI"):
                for scenario, rows in parent_ryt[parameter].items():
                    row = one(rows, TechId=tid)
                    for y in build.YEARS:
                        value = row[y]
                        if value is not None and abs(float(value)) > TOL:
                            removed_errors.append([name, parameter, scenario, y, value])
        check("removed_gas_variants_were_structurally_unreachable_in_parent", not removed_errors, removed_errors[:20])

        fx = float(spatial["exchange_rate"]["php_per_usd_2019"])
        conversion = (1e9 / 3.6) / fx / 1e6
        rytm = load(case, "RYTM.json")
        cost_errors = []
        for node, increment in spatial["transmission"]["node_increment_php_per_kwh"].items():
            tid = tech[f"PHL_POW_TD_{node}"]["TechId"]
            row = one(rytm["VC"][build.SC_BASE], TechId=tid, MoId=1)
            expected = float(increment) * conversion
            for y in build.YEARS:
                if not close(row[y], expected): cost_errors.append(["TD", node, y, row[y], expected])
        wheeling = float(spatial["transmission"]["interconnector_pds_proxy_php_per_kwh"]) * conversion
        for key in ("LV", "VM"):
            tid = tech[f"PHL_POW_INT_{key}"]["TechId"]
            for mode in (1, 2):
                row = one(rytm["VC"][build.SC_BASE], TechId=tid, MoId=mode)
                for y in build.YEARS:
                    if not close(row[y], wheeling): cost_errors.append(["INT", key, mode, y, row[y], wheeling])
        check("sourced_node_grid_and_interconnector_costs_exact", not cost_errors, cost_errors[:20])

        resource_errors = []
        durations = {row["TsId"]: row for row in load(case, "RYTs.json")["YS"][build.SC_BASE]}
        cf_rows = rytt["CF"][build.SC_BASE]
        renewable_specs = (spatial["renewables"]["solar"], spatial["renewables"]["onshore_wind"])
        for spec in renewable_specs:
            base = spec["technology"]
            source_fx = float(spec["source_exchange_rate_php_per_usd"])
            anchors = {
                "CC": float(spec["capital_cost_php_million_per_mw"]) / source_fx * 1000.0,
                "FC": float(spec["fixed_om_php_million_per_mw_year"]) / source_fx * 1000.0,
            }
            for node in build.NODES:
                tid = tech[f"{base}_{node}"]["TechId"]
                for parameter, expected in anchors.items():
                    actual = one(ryt[parameter][build.SC_BASE], TechId=tid)["2024"]
                    if not close(actual, expected): resource_errors.append([base, node, parameter, actual, expected])
                expected_cap = float(spec["gross_crez_potential_mw"][node]) / 1000.0
                total = one(ryt["TAMaxC"][build.SC_BASE], TechId=tid)
                for y in build.YEARS:
                    if not close(total[y], expected_cap): resource_errors.append([base, node, "TAMaxC", y, total[y], expected_cap])
                rows = [row for row in cf_rows if row["TechId"] == tid]
                expected_cf = float(spec["capacity_factor_midpoint"][node])
                for y in build.YEARS:
                    actual_cf = sum(float(row[y]) * float(durations[row["TsId"]][y]) for row in rows)
                    if not close(actual_cf, expected_cf): resource_errors.append([base, node, "weighted_CF", y, actual_cf, expected_cf])
                    if any(float(row[y]) < -TOL or float(row[y]) > 1.0 + TOL for row in rows):
                        resource_errors.append([base, node, "CF_out_of_range", y])
        check("renewable_cost_cf_and_physical_potential_inputs_exact", not resource_errors, resource_errors[:20])

    def max_capacity(tid: str, year: str) -> float:
        """CAa1/CAa2 upper envelope: RC plus every surviving allowed new vintage."""
        rc = float(one(ryt["RC"][build.SC_BASE], TechId=tid)[year])
        life = int(float(rt["OL"][build.SC_BASE][0][tid]))
        inc_row = one(ryt["TAMaxCI"][build.SC_BASE], TechId=tid)
        total_row = one(ryt["TAMaxC"][build.SC_BASE], TechId=tid)
        y = int(year)
        surviving_new = sum(max(0.0, float(inc_row[v])) for v in build.YEARS if int(v) <= y and y - int(v) < life)
        capacity = rc + surviving_new
        total_limit = float(total_row[year])
        if total_limit >= 0:
            capacity = min(capacity, total_limit)
        return max(0.0, capacity)

    # Constructive historical reserve witness using the exact stock/vintage envelope.
    reserve_shortfalls = []
    for con in gen["osy-constraints"]:
        if not con["Con"].startswith("PHL_POW_RESERVE_MARGIN_"): continue
        node = con["Con"].rsplit("_", 1)[-1]
        for y in build.HISTORY:
            firm = 0.0
            for tid in con["CM"]:
                ccm = one(rytcn["CCM"][build.SC_BASE], TechId=tid, ConId=con["ConId"])
                firm += max_capacity(tid, y) * -float(ccm[y])
            required = 1.25 * float(inputs["peak_mw"][y][node]) / 1000.0
            if firm + TOL < required: reserve_shortfalls.append([node, y, firm, required])
    check("historical_node_residual_stock_meets_reserve_before_optimization", not reserve_shortfalls, reserve_shortfalls)

    # Constructive all-year network envelope against the unchanged v36 BASE electricity-use witness.
    base_use = annual_baseline_grid_use()
    energy_shortfalls, peak_shortfalls = [], []
    gen_ids = {n: [r["TechId"] for r in grid_generators if r["Tech"].endswith("_" + n)] for n in build.NODES}
    ts_ids = [r["TsId"] for r in gen["osy-ts"]]
    total_sales_share = {y: build.shares(build.history_values(inputs, y if y in build.HISTORY else "2024", "sales_gwh")) for y in build.YEARS}
    for y in build.YEARS:
        # Maximum possible capacity follows CAa1/CAa2: residual plus all surviving
        # allowed new vintages, capped by the per-technology total-capacity limit.
        maxcap = {}
        for node in build.NODES:
            maxcap[node] = {}
            for tid in gen_ids[node]:
                maxcap[node][tid] = max_capacity(tid, y)
            annual = sum(maxcap[node][tid] * float(one(ryt["AF"][build.SC_BASE], TechId=tid)[y]) * 31.536 for tid in gen_ids[node])
            need = base_use[y] * total_sales_share[y][node]
            incident = sum(float(one(ryt["RC"][build.SC_BASE], TechId=r["TechId"])[y]) * 31.536 * .97 for r in connector_rows if node in r["Tech"] or True)
            # Each link is filtered by its endpoint commodity names below; the raw sum is only an upper envelope.
            incident = 0.0
            for r in connector_rows:
                if any(comm[f"PHL_POW_ELE_{node}"]["CommId"] in r[k] for k in ("IAR", "OAR")):
                    incident += float(one(ryt["RC"][build.SC_BASE], TechId=r["TechId"])[y]) * 31.536 * .97
            if annual + incident + TOL < need: energy_shortfalls.append([node, y, annual, incident, need])
        # Every-timeslice physical envelope is checked against a conservative projected peak.
        projected_peak = sum(float(inputs["peak_mw"]["2024"][n]) / 1000.0 * (base_use[y] / base_use["2024"]) for n in build.NODES)
        for ts in ts_ids:
            supply = 0.0
            for node in build.NODES:
                supply += sum(maxcap[node][tid] * float(one(rytt["CF"][build.SC_BASE], TechId=tid, TsId=ts)[y]) for tid in gen_ids[node])
            if supply + TOL < projected_peak: peak_shortfalls.append([y, ts, supply, projected_peak])
    check("all_year_energy_envelope_meets_v36_demand_witness", not energy_shortfalls, energy_shortfalls[:20])
    check("every_year_every_timeslice_capacity_envelope_meets_projected_peak_witness", not peak_shortfalls, peak_shortfalls[:20])

    # Required policy scenarios retain each split member and no target is numerically tripled.
    scenario_ids = {r["Scenario"]: r["ScenarioId"] for r in gen["osy-scenarios"]}
    check("four_required_scenarios_present", {"BASE", "COAL_PHASEOUT", "RE", "EV"} <= set(scenario_ids), scenario_ids)
    policy_errors = []
    for con_name in ("RENEWABLES", "NUCLEAR_CAPACITY_TARGET", "EV"):
        con = next(c for c in gen["osy-constraints"] if c["Con"] == con_name)
        if len(con["CM"]) != len(set(con["CM"])): policy_errors.append([con_name, "duplicate members"])
    check("national_policy_constraints_aggregate_split_members_once", not policy_errors, policy_errors)

    failures = [c for c in checks if c["status"] == "fail"]
    report = {
        "case": case_identity, "status": "pass_zero_solve" if not failures else "fail_stop_before_generation",
        "optimizer_runs": 0, "generation_runs": 0, "failure_count": len(failures),
        "baseline_witness": "sealed Philippines_v36 BASE annual electricity use; benchmark only",
        "checks": checks,
    }
    suffix = "vIS12" if is_v12 else "vIS11"
    out = case / f"documentation/preflight_island_power_{suffix}.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "failure_count": len(failures), "failures": [f["name"] for f in failures]}, indent=2))
    if failures: raise SystemExit(1)


if __name__ == "__main__":
    main()
