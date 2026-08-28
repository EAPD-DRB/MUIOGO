#!/usr/bin/env python3
"""Verify that vIS1.x source topology and values survived MUIOGO generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import build_philippines_vis1 as build


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "WebAPP/DataStorage/.Philippines_vIS11-candidate-20260828"
DEFAULT_RUN = "BASE_VIS11_STABILIZED"
TOL = 1e-10


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(rows: list[dict], **coords: object) -> dict:
    found = [r for r in rows if all(r.get(k) == v for k, v in coords.items())]
    if len(found) != 1: raise RuntimeError(f"Expected one row at {coords}, found {len(found)}")
    return found[0]


def section(text: str, parameter: str) -> tuple[float, str]:
    match = re.search(rf"param {re.escape(parameter)} default ([^ ]+) :=\s*(.*?)\n;", text, re.S)
    if not match: raise RuntimeError(f"Missing generated parameter {parameter}")
    return float(match.group(1)), match.group(2)


def vector(text: str, parameter: str, technology: str) -> list[float]:
    default, body = section(text, parameter)
    for line in body.splitlines():
        parts = line.split()
        if parts and parts[0] == technology:
            return [float(x) for x in parts[1:]]
    return [default] * len(build.YEARS)


def block(text: str, parameter: str, technology: str, mode: int, commodity: str) -> list[float]:
    default, body = section(text, parameter)
    match = re.search(
        rf"\[RE1,{re.escape(technology)},{re.escape(commodity)},\*,\*\]:\s*\n"
        rf"2020(?:\s+\d{{4}}){{33}}\s*:=\s*\n(.*?)(?=\n\[RE1,|\Z)", body, re.S,
    )
    if not match: return [default] * len(build.YEARS)
    for line in match.group(1).splitlines():
        parts = line.split()
        if parts and parts[0] == str(mode): return [float(x) for x in parts[1:]]
    return [default] * len(build.YEARS)


def indexed_block(text: str, parameter: str, technology: str, index: str) -> list[float]:
    """Read a [REGION,TECHNOLOGY,*,*] matrix row (mode or timeslice)."""
    default, body = section(text, parameter)
    match = re.search(
        rf"\[RE1,{re.escape(technology)},\*,\*\]:\s*\n"
        rf"2020(?:\s+\d{{4}}){{33}}\s*:=\s*\n(.*?)(?=\n\[RE1,|\Z)", body, re.S,
    )
    if not match: return [default] * len(build.YEARS)
    for line in match.group(1).splitlines():
        parts = line.split()
        if parts and parts[0] == str(index): return [float(x) for x in parts[1:]]
    return [default] * len(build.YEARS)


def same(actual: list[float], source: dict) -> bool:
    expected = [float(source[y]) for y in build.YEARS]
    return len(actual) == len(expected) and all(abs(a-b) <= TOL * max(1.0, abs(b)) for a,b in zip(actual, expected))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=CASE)
    parser.add_argument("--run", default=DEFAULT_RUN)
    args = parser.parse_args()
    case, run = args.case.resolve(), args.case.resolve() / "res" / args.run
    data = (run / "data.txt").read_text(encoding="utf-8")
    processed = (run / "data_processed.txt").read_text(encoding="utf-8")
    generation = json.loads((run / "generation_matrix_report.json").read_text())
    gen = json.loads((case / "genData.json").read_text())
    case_identity = gen.get("osy-casename")
    is_v12 = case_identity == "Philippines_vIS1.2"
    suffix = "vIS12" if is_v12 else "vIS11"
    preflight = json.loads((case / f"documentation/preflight_island_power_{suffix}.json").read_text())
    ryt = json.loads((case / "RYT.json").read_text())
    rycn = json.loads((case / "RYCn.json").read_text())
    rytcm = json.loads((case / "RYTCM.json").read_text())
    rytm = json.loads((case / "RYTM.json").read_text())
    rytts = json.loads((case / "RYTTs.json").read_text())
    ids = {r["Tech"]: r["TechId"] for r in gen["osy-tech"]}
    comms = {r["Comm"]: r["CommId"] for r in gen["osy-comm"]}
    timeslices = {r["TsId"]: str(r["Ts"]) for r in gen["osy-ts"]}
    checks = []
    def check(name: str, passed: bool, detail: object = "") -> None:
        checks.append({"name": name, "status": "pass" if passed else "fail", "detail": detail})

    check("source_preflight_still_clean", preflight.get("status") == "pass_zero_solve" and preflight.get("failure_count") == 0)
    check("case_identity_generated", "set TECHNOLOGY" in data and case_identity in ("Philippines_vIS1.1", "Philippines_vIS1.2"))
    for node in build.NODES:
        td_name = f"PHL_POW_TD_{node}"
        tid = ids[td_name]
        source = one(rytcm["IAR"][build.SC_BASE], TechId=tid, CommId=comms[f"PHL_POW_ELE_{node}"], MoId=1)
        check(f"td_loss_series_{node}", same(block(data, "InputActivityRatio", td_name, 1, f"PHL_POW_ELE_{node}"), source))
        out_set = processed.split(f"set MODExTECHNOLOGYperFUELout[PHL_POW_ELE_{node}]:=", 1)
        check(f"node_output_mapping_{node}", len(out_set) == 2 and any(f"_{node})" in x for x in out_set[1].split(";",1)[0].splitlines()))
    for key, spec in json.loads(build.INPUT.read_text())["interconnectors"].items():
        name, tid = f"PHL_POW_INT_{key}", ids[f"PHL_POW_INT_{key}"]
        check(f"interconnector_capacity_{key}", same(vector(data, "ResidualCapacity", name), one(ryt["RC"][build.SC_BASE], TechId=tid)))
        mode_match = re.search(rf"set MODEperTECHNOLOGY\[{re.escape(name)}\]:=\s*([^;]+);", processed)
        derived_modes = set(mode_match.group(1).split()) if mode_match else set()
        check(f"interconnector_two_modes_{key}", derived_modes == {"1", "2"}, sorted(derived_modes))
        a, b = spec["from"], spec["to"]
        for parameter, source_name, commodity, mode in (
            ("InputActivityRatio", "IAR", f"PHL_POW_ELE_{a}", 1),
            ("OutputActivityRatio", "OAR", f"PHL_POW_ELE_{b}", 1),
            ("InputActivityRatio", "IAR", f"PHL_POW_ELE_{b}", 2),
            ("OutputActivityRatio", "OAR", f"PHL_POW_ELE_{a}", 2),
        ):
            source = one(rytcm[source_name][build.SC_BASE], TechId=tid, CommId=comms[commodity], MoId=mode)
            check(f"{key}_{parameter}_{commodity}_m{mode}", same(block(data, parameter, name, mode, commodity), source))
    for tech_name in build.SECTOR_TD:
        tid = ids[tech_name]
        for node in build.NODES:
            commodity = f"PHL_POW_ELE1_{node}"
            source = one(rytcm["IAR"][build.SC_BASE], TechId=tid, CommId=comms[commodity], MoId=1)
            check(f"bundle_{tech_name}_{node}", same(block(data, "InputActivityRatio", tech_name, 1, commodity), source))
    check("no_generated_delivery_pass_throughs", "PHL_PRO_DEL_" not in data)
    if is_v12:
        spatial = json.loads((case / "documentation/spatial_cost_inputs_vIS12.json").read_text())
        for name in spatial["structural_cleanup"]["removed_zero_reachability_node_technologies"]:
            check(f"removed_structural_technology_{name}", name not in data and name not in processed)
        for node in build.NODES:
            name = f"PHL_POW_TD_{node}"
            source = one(rytm["VC"][build.SC_BASE], TechId=ids[name], MoId=1)
            check(f"generated_td_variable_cost_{node}", same(indexed_block(data, "VariableCost", name, "1"), source))
        for link in ("LV", "VM"):
            name = f"PHL_POW_INT_{link}"
            for mode in (1, 2):
                source = one(rytm["VC"][build.SC_BASE], TechId=ids[name], MoId=mode)
                check(f"generated_interconnector_cost_{link}_m{mode}", same(indexed_block(data, "VariableCost", name, str(mode)), source))
        for spec in (spatial["renewables"]["solar"], spatial["renewables"]["onshore_wind"]):
            for node in build.NODES:
                name = f"{spec['technology']}_{node}"
                tid = ids[name]
                check(f"generated_capital_cost_{name}", same(vector(data, "CapitalCost", name), one(ryt["CC"][build.SC_BASE], TechId=tid)))
                check(f"generated_capacity_ceiling_{name}", same(vector(data, "TotalAnnualMaxCapacity", name), one(ryt["TAMaxC"][build.SC_BASE], TechId=tid)))
                for source in [row for row in rytts["CF"][build.SC_BASE] if row["TechId"] == tid]:
                    check(f"generated_cf_{name}_{source['TsId']}", same(indexed_block(data, "CapacityFactor", name, timeslices[source["TsId"]]), source))
    # National gross bus must have no grid-generation output pair after preprocessing.
    national = processed.split("set MODExTECHNOLOGYperFUELout[PHL_POW_ELE]:=", 1)
    national_body = national[1].split(";", 1)[0] if len(national) == 2 else ""
    forbidden = [name for name in build.GENERATION if name in national_body]
    check("no_generated_national_grid_pool", not forbidden, forbidden)
    # Every generated UDC constant must equal the last non-null value among
    # active scenarios for that exact constraint-year cell. This catches both
    # cross-constraint carry and unintended forward-fill of sparse milestones.
    active_names = generation["active_scenarios"]
    scenario_ids = {row["Scenario"]: row["ScenarioId"] for row in gen["osy-scenarios"]}
    constraint_ids = {row["Con"]: row["ConId"] for row in gen["osy-constraints"]}
    default_udc, udc_body = section(data, "UDCConstant")
    generated_udc = {}
    for line in udc_body.splitlines():
        parts = line.split()
        if parts and parts[0] in constraint_ids and len(parts) == len(build.YEARS) + 1:
            generated_udc[parts[0]] = [float(value) for value in parts[1:]]
    udc_source_errors = []
    for name, cid in constraint_ids.items():
        actual = generated_udc.get(name)
        if actual is None:
            udc_source_errors.append([name, "missing_generated_row"])
            continue
        expected = []
        for year in build.YEARS:
            value = default_udc
            for scenario_name in active_names:
                row = one(rycn["UCC"][scenario_ids[scenario_name]], ConId=cid)
                if row[year] is not None:
                    value = float(row[year])
            expected.append(value)
        for year, observed, wanted in zip(build.YEARS, actual, expected):
            if abs(observed - wanted) > TOL:
                udc_source_errors.append([name, year, observed, wanted])
    check("generated_udc_constants_match_active_source_cells", not udc_source_errors,
          udc_source_errors[:20])
    # GLPK represents an empty equality LHS with a zero coefficient on a
    # placeholder variable. A non-zero RHS makes such a row deterministically
    # infeasible, so reject it before CBC.
    lp = (run / "lp.lp").read_text(encoding="utf-8")
    empty_nonzero_equalities = []
    pattern = re.compile(
        r"^ (UDC2_UserDefinedConstraintEquality\([^\n:]+\)): 0 [^\n]+\n"
        r" = ([-+0-9.eE]+)$",
        re.M,
    )
    for label, rhs in pattern.findall(lp):
        if abs(float(rhs)) > TOL:
            empty_nonzero_equalities.append([label, float(rhs)])
    check("no_empty_lhs_nonzero_rhs_udc_equalities", not empty_nonzero_equalities,
          empty_nonzero_equalities[:20])
    hash_checks = {name: sha256(run / name) == digest for name, digest in generation["hashes"].items()}
    check("generated_artifacts_unchanged_after_matrix_check", all(hash_checks.values()), hash_checks)
    failures = [c for c in checks if c["status"] == "fail"]
    report = {
        "status": "pass_generated_zero_solve" if not failures else "fail_stop_before_base",
        "failure_count": len(failures), "optimizer_runs": 0,
        "matrix_dimensions": generation["matrix_dimensions"], "matrix_deltas": generation["matrix_deltas"],
        "checks": checks,
    }
    output = "generated_island_power_gate_vis12.json" if is_v12 else "generated_island_power_gate_vis11.json"
    (run / output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "failure_count": len(failures), "failures": [c["name"] for c in failures]}, indent=2))
    if failures: raise SystemExit(1)


if __name__ == "__main__":
    main()
