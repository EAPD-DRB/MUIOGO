"""Read-only helpers over a MUIOGO case directory.

The link is permitted to READ MUIOGO's filesystem (the same reads the forward pass
already does); every WRITE still goes through the applyPatch endpoint. These helpers
supply the builder with the case's base demand rows, its year horizon, and the set of
scenarios active in a target caserun -- all read exactly as applyPatch reads them, so
"what we scaled" matches "what gets overwritten".

All case JSON is read with utf-8-sig: MUIOGO writes these files with a BOM.
"""
from __future__ import annotations

import json
import os


def _read_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def read_base_sad(case_dir, scenario, comm_code) -> dict[int, float]:
    """The base Specified Annual Demand for ``comm_code`` under ``scenario``, as {year: value}.

    Maps the human commodity code to its per-case CommId via genData.json osy-comm, then
    finds that row in RYC.json SAD[scenario] and returns every numeric-year cell as int->float.
    Fails loudly (listing what exists) on a missing commodity, scenario, or row.
    """
    assert isinstance(case_dir, str) and case_dir, "case_dir must be a non-empty path"
    assert isinstance(scenario, str) and scenario, "scenario must be a non-empty string"
    assert isinstance(comm_code, str) and comm_code, "comm_code must be a non-empty string"

    gen = _read_json(os.path.join(case_dir, "genData.json"))
    comm_by_code = {c["Comm"]: c["CommId"] for c in gen.get("osy-comm", [])}
    comm_id = comm_by_code.get(comm_code)
    if comm_id is None:
        raise KeyError(
            f"commodity {comm_code!r} is not in case {case_dir!r}; known commodities: "
            f"{sorted(comm_by_code)}")

    sad = _read_json(os.path.join(case_dir, "RYC.json")).get("SAD", {})
    rows = sad.get(scenario)
    if rows is None:
        raise KeyError(
            f"scenario {scenario!r} has no SAD table in case {case_dir!r}; present: "
            f"{sorted(sad)}")

    row = next((r for r in rows if r.get("CommId") == comm_id), None)
    if row is None:
        raise KeyError(
            f"SAD[{scenario}] has no row for {comm_code!r} ({comm_id}) in case {case_dir!r}")

    out: dict[int, float] = {}
    for key, val in row.items():
        if key == "CommId":
            continue
        try:
            year = int(key)
        except (TypeError, ValueError):
            continue
        out[year] = float(val)
    return out


def read_case_years(case_dir) -> set[int]:
    """The case's model years, from genData.json osy-years, as a set of ints."""
    assert isinstance(case_dir, str) and case_dir, "case_dir must be a non-empty path"
    gen = _read_json(os.path.join(case_dir, "genData.json"))
    years = gen.get("osy-years")
    assert years, f"case {case_dir!r} has no osy-years in genData.json"
    return {int(y) for y in years}


def read_active_scenarios(case_dir, base_caserun) -> set[str]:
    """The set of ScenarioIds active in ``base_caserun`` -- mirrors PatchApply.base_caserun_record.

    Reads view/resData.json osy-cases, finds the record whose Case == base_caserun (raising,
    with the present caseruns listed, if absent), and returns the Active scenarios' ScenarioIds.
    """
    assert isinstance(case_dir, str) and case_dir, "case_dir must be a non-empty path"
    assert isinstance(base_caserun, str) and base_caserun, "base_caserun must be a non-empty string"

    res = _read_json(os.path.join(case_dir, "view", "resData.json"))
    cases = res.get("osy-cases", [])
    record = next((c for c in cases if c.get("Case") == base_caserun), None)
    if record is None:
        raise KeyError(
            f"caserun {base_caserun!r} does not exist in case {case_dir!r}; present: "
            f"{[c.get('Case') for c in cases]}")
    return {s["ScenarioId"] for s in record.get("Scenarios", []) if s.get("Active")}
