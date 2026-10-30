"""Read effective MUIOGO parameter values without importing the application.

Match DataFile.gen_RYC/gen_RYE: defaults are overlaid by non-null values from
active scenarios in the caserun's stored order. Never sort that order.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


def read_json(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def read_case_years(case_dir):
    years = read_json(Path(case_dir) / "genData.json").get("osy-years")
    if not years:
        raise ValueError(f"case {str(case_dir)!r} has no model years")
    return {int(year) for year in years}


def read_active_scenario_order(case_dir, caserun):
    records = read_json(Path(case_dir) / "view/resData.json").get("osy-cases", [])
    record = next((r for r in records if r.get("Case") == caserun), None)
    if record is None:
        raise ValueError(f"unknown caserun {caserun!r}; present: {[r.get('Case') for r in records]}")
    active = [s["ScenarioId"] for s in record["Scenarios"] if s.get("Active") == True]
    if not active or len(active) != len(set(active)):
        raise ValueError(f"caserun {caserun!r} must have distinct active scenarios")
    return active


def select_write_scenario(active_order, requested=None):
    """Use the final active layer for both demand and optional emissions edits."""
    if not active_order:
        raise ValueError("caserun has no active scenarios")
    highest = active_order[-1]
    if requested is not None and requested != highest:
        raise ValueError(
            f"--scenario must be the last active scenario {highest!r}; "
            f"{requested!r} may be overridden by later active scenarios")
    return highest


def _effective_values(case_dir, caserun, code, *, dimension, parameter, registry, code_key, id_key):
    case_dir = Path(case_dir)
    gen = read_json(case_dir / "genData.json")
    ids = {r[code_key]: r[id_key] for r in gen.get(registry, [])}
    if code not in ids:
        raise ValueError(f"unknown {code_key} code {code!r}; present: {sorted(ids)}")
    years = read_case_years(case_dir)
    params = read_json(case_dir.parent / "Parameters.json")
    definition = next((p for p in params[dimension] if p["id"] == parameter), None)
    if definition is None:
        raise ValueError(f"no default defined for {parameter}")
    default = float(definition["default"])
    if not math.isfinite(default) or default < 0:
        raise ValueError(f"invalid {parameter} default {default}")
    values = dict.fromkeys(years, default)
    tables = read_json(case_dir / f"{dimension}.json").get(parameter, {})
    for scenario in read_active_scenario_order(case_dir, caserun):
        rows = tables.get(scenario, [])
        matching = [r for r in rows if r.get(id_key) == ids[code]]
        if len(matching) != 1:
            raise ValueError(f"expected one {parameter}[{scenario}] row for {code!r}")
        row = matching[0]
        for year in years:
            key = str(year)
            if key not in row:
                raise ValueError(f"missing {parameter}[{scenario}][{code}][{year}]")
            if row[key] is not None:
                value = float(row[key])
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"invalid {parameter}[{scenario}][{code}][{year}]")
                values[year] = value
    return values


def read_effective_sad(case_dir, caserun, comm_code):
    return _effective_values(case_dir, caserun, comm_code, dimension="RYC", parameter="SAD",
                             registry="osy-comm", code_key="Comm", id_key="CommId")


def read_effective_penalty(case_dir, caserun, emission_code):
    return _effective_values(case_dir, caserun, emission_code, dimension="RYE", parameter="EP",
                             registry="osy-emis", code_key="Emis", id_key="EmisId")
