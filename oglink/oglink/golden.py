"""Golden-record capture for the test battery: extract key OG-Core macro aggregates from a
run's SS/TPI result dict into a flat, persistable record, and diff a fresh run against a
committed baseline. Pure (numpy only) -- no solving, no ogcore import, so it stays testable.

A record: ``{"run": name, "base": {...}, "reform": {...}, "pct_diff": {...}}``. SS values are
scalars; TPI values are arrays, recorded as t0 / ~10y / SS. The committed baseline lives in
``results/golden.json`` (a ``{run -> record}`` table); after the first battery run, commit it,
and every later run diffs against it via ``check``. CEV/welfare is captured separately by the
viz/report layer (it needs model params), not here.
"""
from __future__ import annotations

import json
import os

import numpy as np

AGG_KEYS = ("Y", "C", "K", "L", "r", "w")
DEFAULT_PATH = os.path.join("results", "golden.json")


def aggregates(result) -> dict:
    """Flatten an OG-Core SS or TPI result dict to ``{key: value}``. Scalars (SS) stay scalar;
    arrays (TPI) become ``<key>_t0`` / ``<key>_t10`` / ``<key>_ss``; ``Y_m`` -> the SS/last
    industry vector. Missing keys are skipped (so SS and TPI dicts both work)."""
    out: dict = {}
    if not result:
        return out
    for k in AGG_KEYS:
        v = result.get(k)
        if v is None:
            continue
        a = np.atleast_1d(np.asarray(v, dtype=float)).ravel()
        if a.size == 1:
            out[k] = float(a[0])
        else:
            out[f"{k}_t0"] = float(a[0])
            out[f"{k}_t10"] = float(a[min(10, a.size - 1)])
            out[f"{k}_ss"] = float(a[-1])
    ym = result.get("Y_m")
    if ym is not None:
        a = np.asarray(ym, dtype=float)
        row = a[-1] if a.ndim == 2 else a            # last TPI period, or the SS vector
        out["Y_m"] = [float(x) for x in np.atleast_1d(row).ravel()]
    return out


def _pct(reform: dict, base: dict) -> dict:
    return {k: 100.0 * (reform[k] - b) / b
            for k, b in base.items()
            if isinstance(b, (int, float)) and b != 0 and isinstance(reform.get(k), (int, float))}


def capture(name: str, base, reform=None) -> dict:
    """Build a golden record from a run's base (and optional reform) result dict."""
    rec = {"run": name, "base": aggregates(base)}
    if reform is not None:
        rec["reform"] = aggregates(reform)
        rec["pct_diff"] = _pct(rec["reform"], rec["base"])
    return rec


def from_context(name: str, ctx) -> dict:
    """Build a record from a framework ExperimentContext (its ``base_tpi`` / ``reform_tpi``)."""
    return capture(name, getattr(ctx, "base_tpi", None), getattr(ctx, "reform_tpi", None))


# --- persistence: results/golden.json is the committed {run -> record} baseline ------------

def load(path: str = DEFAULT_PATH) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def save(record: dict, path: str = DEFAULT_PATH) -> dict:
    """Upsert a record into the JSON table at ``path`` (creating it). Returns the full table."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    table = load(path)
    table[record["run"]] = record
    with open(path, "w", encoding="utf-8") as f:
        json.dump(table, f, indent=2, sort_keys=True)
    return table


# --- regression check ----------------------------------------------------------------------

def _flat(rec: dict) -> dict:
    """Flatten a record's numeric leaves to ``{dotted_key: float}`` for comparison."""
    out: dict = {}
    for sect in ("base", "reform", "pct_diff"):
        for k, v in rec.get(sect, {}).items():
            if isinstance(v, (int, float)):
                out[f"{sect}.{k}"] = float(v)
            elif isinstance(v, list):
                for i, x in enumerate(v):
                    out[f"{sect}.{k}[{i}]"] = float(x)
    return out


def compare(current: dict, golden: dict, rtol: float = 1e-6, atol: float = 1e-9) -> dict:
    """Diff two records numerically. Returns ``{match: bool, diffs: {key: (golden, current)}}``."""
    cur, gold = _flat(current), _flat(golden)
    diffs = {}
    for k in sorted(set(cur) | set(gold)):
        a, b = gold.get(k), cur.get(k)
        if a is None or b is None or abs(a - b) > atol + rtol * abs(a):
            diffs[k] = (a, b)
    return {"match": not diffs, "diffs": diffs}


def check(name: str, base, reform=None, path: str = DEFAULT_PATH, rtol: float = 1e-6) -> dict:
    """Capture a fresh record for ``name`` and compare it to the committed golden baseline.
    Returns ``{match, diffs, record, had_golden}``. ``match`` is ``None`` when no baseline
    exists yet -- capture it with ``save()`` and commit ``golden.json`` to establish one."""
    rec = capture(name, base, reform)
    table = load(path)
    if name not in table:
        return {"match": None, "diffs": {}, "record": rec, "had_golden": False}
    cmp = compare(rec, table[name], rtol=rtol)
    return {"match": cmp["match"], "diffs": cmp["diffs"], "record": rec, "had_golden": True}
