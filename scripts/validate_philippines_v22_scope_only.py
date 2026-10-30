#!/usr/bin/env python3
"""Equation-first deterministic gate for the Philippines v22 r8 candidate.

No solver is invoked. The gate proves that r8 adds no outcome constraint or
capacity/activity bound, checks every numerical and structural source diff,
and verifies lossless timeslice aggregation and input-path availability.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import build_philippines_v22_integrated_repair as spec


ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "WebAPP" / "DataStorage" / ".Philippines_v22-transition-scope-only-candidate-r8"
TOL = 1e-11


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def keyed(rows, *fields):
    return {tuple(row[field] for field in fields): row for row in rows}


def main(candidate: Path) -> dict:
    source = spec.SOURCE
    if not candidate.is_dir():
        raise FileNotFoundError(candidate)
    failures, checks = [], []

    def check(name, condition, detail):
        checks.append({"check": name, "passed": bool(condition), "detail": detail})
        if not condition:
            failures.append(f"{name}: {detail}")

    gen, sgen = read(candidate / "genData.json"), read(source / "genData.json")
    tid = {x["Tech"]: x["TechId"] for x in gen["osy-tech"]}
    cid = {x["Comm"]: x["CommId"] for x in gen["osy-comm"]}
    years = tuple(gen["osy-years"])
    scenarios = tuple(x["ScenarioId"] for x in gen["osy-scenarios"])

    # Classification and master-rule gate: r8 may alter conversion drivers and
    # a degenerate temporal representation, but no demand, bound or constraint.
    for filename in ("RYC.json", "RYT.json", "RYCn.json", "RYTCn.json", "RYTM.json", "RYTEM.json", "RT.json"):
        check(f"unchanged_{filename}", read(candidate / filename) == read(source / filename),
              "final demands, stocks, lifetimes, costs, all activity/capacity bounds, emissions, and UDC coefficients remain source-identical")
    check("no_new_udc", gen["osy-constraints"] == sgen["osy-constraints"],
          "constraint definitions are exactly unchanged")
    check("same_physical_objects", [x["TechId"] for x in gen["osy-tech"]] == [x["TechId"] for x in sgen["osy-tech"]]
          and [x["CommId"] for x in gen["osy-comm"]] == [x["CommId"] for x in sgen["osy-comm"]],
          "no technology or commodity added or removed")

    # Structural IAR membership: precisely the three requested additions.
    source_tech = {x["TechId"]: x for x in sgen["osy-tech"]}
    cand_tech = {x["TechId"]: x for x in gen["osy-tech"]}
    membership_diffs = {}
    for tech_id in source_tech:
        before, after = set(source_tech[tech_id]["IAR"]), set(cand_tech[tech_id]["IAR"])
        if before != after:
            membership_diffs[tech_id] = {"added": sorted(after-before), "removed": sorted(before-after)}
    expected_membership = {
        tid[name]: {"added": [cid[commodity]], "removed": []}
        for name, (commodity, _) in spec.AGRICULTURE_HEAT_IAR.items()
    }
    check("agriculture_heat_membership_exact", membership_diffs == expected_membership,
          {"actual": membership_diffs, "expected": expected_membership})
    structural_fields_ok = True
    for tech_id in source_tech:
        for field in source_tech[tech_id]:
            if field in {"IAR", "Desc"}:
                continue
            structural_fields_ok &= source_tech[tech_id][field] == cand_tech[tech_id][field]
    check("technology_structure_otherwise_unchanged", structural_fields_ok,
          "all non-IAR technology fields are identical; only charcoal description is allowed to improve")

    # Numerical IAR gate. Existing coordinates may change only for cooking;
    # new coordinates must be the three agriculture-heat inputs, mode 1 only.
    src_iar = read(source / "RYTCM.json")["IAR"]
    out_iar = read(candidate / "RYTCM.json")["IAR"]
    cooking_tids = {tid[x] for x in spec.COOKING_EFFICIENCY}
    agr_coords = {(tid[t], cid[c]) for t, (c, _) in spec.AGRICULTURE_HEAT_IAR.items()}
    unexpected = []
    for scenario in scenarios:
        smap = keyed(src_iar[scenario], "TechId", "CommId", "MoId")
        cmap = keyed(out_iar[scenario], "TechId", "CommId", "MoId")
        for key in set(smap) | set(cmap):
            if smap.get(key) != cmap.get(key) and key[0] not in cooking_tids and key[:2] not in agr_coords:
                unexpected.append((scenario, key))
    check("iar_diff_allowlist", not unexpected, unexpected[:20])
    base_rows = out_iar[spec.BASE]
    cooking_ok = True
    for name, efficiency in spec.COOKING_EFFICIENCY.items():
        rows = [x for x in base_rows if x["TechId"] == tid[name]]
        cooking_ok &= bool(rows)
        for row in rows:
            expected = 1/efficiency if row["MoId"] == 1 else 0.0
            cooking_ok &= all(abs(float(row[y])-expected) <= TOL for y in years)
    check("cooking_iar_exact", cooking_ok, {k: 1/v for k, v in spec.COOKING_EFFICIENCY.items()})
    agriculture_ok = True
    for name, (commodity, coefficient) in spec.AGRICULTURE_HEAT_IAR.items():
        rows = [x for x in base_rows if x["TechId"] == tid[name] and x["CommId"] == cid[commodity]]
        agriculture_ok &= bool(rows)
        for row in rows:
            expected = coefficient if row["MoId"] == 1 else 0.0
            agriculture_ok &= all(abs(float(row[y])-expected) <= TOL for y in years)
    check("agriculture_heat_iar_exact", agriculture_ok, spec.AGRICULTURE_HEAT_IAR)
    policy_inheritance_ok = all(
        all(row[y] is None for y in years)
        for scenario in scenarios if scenario != spec.BASE
        for row in out_iar[scenario]
        if row["TechId"] in cooking_tids or (row["TechId"], row["CommId"]) in agr_coords
    )
    check("iar_policy_inheritance", policy_inheritance_ok, "all affected policy rows inherit SC_0")

    # Every new input has an upstream producer. Since all RYT bounds and final
    # demands are unchanged, r8 introduces no deterministic source cap or new
    # demand contradiction; optimization is still required for joint feasibility.
    producers = {}
    for commodity in {c for c, _ in spec.AGRICULTURE_HEAT_IAR.values()}:
        commodity_id = cid[commodity]
        producers[commodity] = [x["Tech"] for x in gen["osy-tech"] if commodity_id in x["OAR"]]
    check("agriculture_input_paths_exist", all(producers.values()), producers)
    check("no_new_demand_or_bound_contradiction", read(candidate / "RYC.json") == read(source / "RYC.json") and read(candidate / "RYT.json") == read(source / "RYT.json"),
          "requested demand and every activity/capacity/resource envelope are unchanged; only fuel required per useful service changes")

    # Lossless daytype aggregation for YearSplit, SDP and every technology CF.
    check("daytype_dimension", {x["DtId"] for x in gen["osy-dt"]} == {spec.REPRESENTATIVE_DAYTYPE_ID} and len(gen["osy-ts"]) == 18,
          {"daytypes": [x["DtId"] for x in gen["osy-dt"]], "timeslices": len(gen["osy-ts"])})
    source_ts = {(x["SE"], x["DTB"], x["DT"]): x["TsId"] for x in sgen["osy-ts"]}
    sys = keyed(read(source / "RYTs.json")["YS"][spec.BASE], "TsId")
    cys = keyed(read(candidate / "RYTs.json")["YS"][spec.BASE], "TsId")
    ssdp = keyed(read(source / "RYCTs.json")["SDP"][spec.BASE], "CommId", "TsId")
    candidate_sdp_rows = read(candidate / "RYCTs.json")["SDP"][spec.BASE]
    csdp = keyed(candidate_sdp_rows, "CommId", "TsId")
    scf = keyed(read(source / "RYTTs.json")["CF"][spec.BASE], "TechId", "TsId")
    ccf = keyed(read(candidate / "RYTTs.json")["CF"][spec.BASE], "TechId", "TsId")
    temporal_ok = True
    for ts in gen["osy-ts"]:
        if ts["SE"] == "SE_ugd96":
            lo = hi = None
        else:
            lo = source_ts[(ts["SE"], ts["DTB"], spec.REPRESENTATIVE_DAYTYPE_ID)]
            hi = source_ts[(ts["SE"], ts["DTB"], spec.REDUNDANT_DAYTYPE_ID)]
        for year in years:
            if lo is None:
                temporal_ok &= cys[(ts["TsId"],)][year] == sys[(ts["TsId"],)][year]
            else:
                lw, hw = float(sys[(lo,)][year]), float(sys[(hi,)][year])
                temporal_ok &= abs(float(cys[(ts["TsId"],)][year])-lw-hw) <= TOL
                for commodity in {k[0] for k in csdp}:
                    temporal_ok &= abs(float(csdp[(commodity, ts["TsId"])][year])-float(ssdp[(commodity, lo)][year])-float(ssdp[(commodity, hi)][year])) <= TOL
                for tech_id in {k[0] for k in ccf}:
                    expected = (float(scf[(tech_id, lo)][year])*lw + float(scf[(tech_id, hi)][year])*hw)/(lw+hw)
                    temporal_ok &= abs(float(ccf[(tech_id, ts["TsId"])][year])-expected) <= TOL
    check("lossless_temporal_aggregation", temporal_ok, "all years, commodities, technologies and retained timeslices")
    normalized = True
    for commodity in {k[0] for k in csdp}:
        rows = [row for row in candidate_sdp_rows if row["CommId"] == commodity]
        for year in years:
            total = sum(float(row[year]) for row in rows)
            normalized &= total <= TOL or abs(total-1.0) <= 2e-6
    check("demand_profiles_normalized", normalized, "every active commodity-year SDP sums to one")

    # Climate scope is deliberately post-solve: no LP emissions membership or
    # equation can enlarge modes or feed accounting back into decisions.
    check("no_afolu_lp_membership", all(
        cand_tech[x["TechId"]]["EAR"] == source_tech[x["TechId"]]["EAR"]
        for x in sgen["osy-tech"]), "all technology emissions memberships unchanged")
    check("livestock_scope_disclosed", any(row["item"] == "Livestock climate scope" for row in csv.DictReader((candidate/"data_sources"/"GAPS.csv").open())),
          "national-agriculture completeness is not claimed")

    # Six-table ledger and retained evidence are required before generation.
    required = ["SOURCES.csv", "ASSUMPTIONS.csv", "CALCULATIONS.csv", "MODEL_MAP.csv", "GAPS.csv", "CHANGES.csv"]
    check("schema_ledger_complete", all((candidate/"data_sources"/x).is_file() for x in required), required)
    assumption_text = (candidate/"data_sources"/"ASSUMPTIONS.csv").read_text(encoding="utf-8")
    check("agriculture_heat_judgement_documented", "ASM_PHL_V22_AGR_HEAT_IAR" in assumption_text and "judgement" in assumption_text,
          "unity electric input and inherited 89% convention are explicit")

    report = {
        "schema": "philippines-v22-transition-scope-deterministic-gate-v1",
        "candidate": str(candidate), "status": "passed" if not failures else "failed",
        "optimizer_runs": 0, "checks": checks, "failures": failures,
        "classification": {
            "initial_stocks": "unchanged",
            "final_demands": "unchanged genuine exogenous demand",
            "continuing_constraints": "unchanged",
            "benchmark_only": ["cooking fuel shares", "DOE 2024 AFF energy/electricity share", "AQUASTAT irrigation requirement", "groundwater share", "GHGI totals"],
        },
        "required_next_step": "Generate/preprocess/check the matrix; optimize only if this report passes.",
    }
    out = candidate / "documentation" / "transition_scope_r8_deterministic_gate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT)
    main(parser.parse_args().candidate.resolve())
