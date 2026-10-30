"""Distill a persisted OG-Core solve log into a concise failure verdict.

When a solve fails, the question is always the same: WHAT phase failed (steady state, the gamma
continuation, or the reform transition path) and WHY (did it converge, hit the iteration cap, diverge
to NaN, or stall?). ``runtime._run`` streams every solve to a ``solve.log``; this reads that file and
returns just enough to answer those questions -- it never reproduces the whole log. Pure text parsing,
no ogcore import, so it runs in the link env.
"""
from __future__ import annotations

import math
import re

_DIST = re.compile(r"Distance:\s*([0-9.eE+-]+|nan|inf)", re.IGNORECASE)
_ITER = re.compile(r"Iteration:\s*(\d+)")
_CONT = re.compile(r"continuation t=([0-9.]+)")
_SS_FAIL = re.compile(r"steady.?state.*(?:not found|could not)", re.IGNORECASE)
# a genuine raised exception starts the line with its type (RuntimeError:, ValueError:, ...). This excludes
# the solver's routine "Max Euler error" / "resource constraint error" noise and benign Dask warnings.
_EXC = re.compile(r"^\s*\w*(?:Error|Exception)\b")


def summarize(log_path: str) -> dict:
    """Return ``{phase, outcome, iters, last_distances, min_distance, error}`` for a solve log, or ``{}``
    if it can't be read. ``outcome`` is a plain verdict; ``phase`` names the solve that was running."""
    try:
        with open(log_path, encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
    except OSError:
        return {}
    if not lines:
        return {}

    # Scope the distance/iteration trail to the LAST solve loop: a log can hold many (each SS continuation
    # step + the final TPI), and each restarts its counter at "Iteration: 1". The phase that actually
    # failed is the last one, so reset on every "Iteration: 1" -- otherwise an SS step that converged to
    # ~1e-15 would masquerade as the min distance of a TPI that never got below 0.8.
    dists, iters, last_cont = [], [], None
    for ln in lines:
        mi = _ITER.search(ln)
        if mi:
            if int(mi.group(1)) == 1:
                dists, iters = [], []
            iters.append(int(mi.group(1)))
        md = _DIST.search(ln)
        if md:
            try:
                dists.append(float(md.group(1)))
            except ValueError:
                dists.append(float("nan"))
        mc = _CONT.search(ln)
        if mc:
            last_cont = mc.group(1)
    finite = [d for d in dists if math.isfinite(d)]
    tail = "\n".join(lines[-80:])

    error = next((ln.strip() for ln in reversed(lines) if _EXC.match(ln) and ln.strip()), "")

    if ("solved reform" in tail or "solved baseline" in tail) and not error:
        phase, outcome = "solve", "converged"
    elif "continuation stalled" in tail:              # check BEFORE the SS pattern -- the stall message
        phase = "gamma continuation"                  # ("...steady state could not be reached") matches both
        outcome = f"stalled at t={last_cont} (reform gamma unreachable)" if last_cont else "stalled"
    elif "Transition path equ" in tail:               # ogcore's exact (typo'd) TPI iteration-cap message
        phase, outcome = "reform TPI", "did not converge (hit iteration cap)"
    elif _SS_FAIL.search(tail):
        phase, outcome = "steady state", "did not converge"
    elif dists and not math.isfinite(dists[-1]):
        phase, outcome = "solve", "diverged (NaN/Inf)"
    else:
        phase, outcome = "solve", "failed"

    return {"phase": phase, "outcome": outcome,
            "iters": max(iters) if iters else None,
            "last_distances": [float(f"{d:.4g}") for d in finite[-3:]],
            "min_distance": float(f"{min(finite):.4g}") if finite else None,
            "error": error[:200]}


def why(d: dict) -> str:
    """A one-line plain-English reason from a ``summarize()`` dict, for the failed-run report/record."""
    if not d:
        return "failed (no solve log found)"
    parts = [f"{d['phase']} {d['outcome']}"]
    if d.get("iters"):
        parts.append(f"{d['iters']} iters")
    if d.get("last_distances"):
        last = d["last_distances"][-1]
        mn = d.get("min_distance")
        parts.append(f"dist {last} (min {mn})" if mn is not None and mn != last else f"dist {last}")
    return ", ".join(parts)
