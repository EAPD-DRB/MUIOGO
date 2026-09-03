"""The coupling orchestrator. A channel is a plain function (see channels.py) that reads/mutates the
coupling state and records provenance. An EXPERIMENT is a function ``exp(ctx, solve)`` that calls
channels in order and calls ``solve(ctx)`` at the point the reform is solved -- pre-solve channels
(clews->og, policy) before it, og->clews ``emit_`` channels after. ``run`` builds the OG baseline (or
reuses a prebuilt one), threads a fresh reform through the experiment, and returns the context.

The solve callables (export_baseline, solve_reform) are INJECTED from runtime.py so this module and the
channels import only numpy and stay unit-testable without ogcore. Those callables drive the country's OG
model in its OWN environment as a subprocess -- this module only ever sees the OGParams template + the
returned solution dicts, never ogcore itself.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

CLEWS_TO_OG = "clews->og"
OG_TO_CLEWS = "og->clews"
POLICY = "policy"


@dataclass
class ExperimentContext:
    """Everything a channel reads or writes during a run (the mutable analogue of OG-Core's ``p``)."""
    country: Any                              # CountryConfig
    concordance: Any = None                   # per-run energy ports DISCOVERED in the OG env + exported
                                              # via baseline_meta.json (the link can't import the country
                                              # package to compute them). None / ports None -> energy
                                              # channels skip (the country can't be coupled on energy).
    og_reform: Any = None                     # Specifications the pre-solve channels mutate
    base_tpi: dict | None = None              # baseline OG outputs (always solved before any channel)
    reform_tpi: dict | None = None            # reform OG outputs (for og->clews channels)
    clews: dict = field(default_factory=dict)
    clews_inputs: dict = field(default_factory=dict)  # OG->CLEWS artifacts to write
    extras: dict = field(default_factory=dict)        # e.g. the mortality shock for the runtime
    provenance: list = field(default_factory=list)

    def log(self, channel: str, **info) -> dict:
        rec = {"channel": channel, **info}
        self.provenance.append(rec)
        return rec


# --- orchestration --------------------------------------------------------------

def _load_concordance(base_dir):
    """The energy-port concordance the OG runner discovered for this baseline and exported to
    ``<base_dir>/baseline_meta.json`` -- the link env can't import the country package to compute it, so
    it reads what the OG env wrote. Absent (older export) -> a fully-unavailable concordance, so the
    energy channels skip rather than crash."""
    import json

    from .contract import Concordance

    meta_path = os.path.join(base_dir, "baseline_meta.json")
    con = None
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8-sig") as f:
            con = json.load(f).get("concordance")
    if not con:
        why = f"no exported concordance in {base_dir}/baseline_meta.json"
        return Concordance(None, None, {"energy_industry_index": why, "energy_good_index": why})
    return Concordance(**con)


def _fresh_reform(template):
    """A clean reform copy of the OGParams template for the next experiment's pre-solve channels to
    mutate. (baseline/baseline_dir/output_base + the e-cache are set runner-side on the real
    Specifications; the template the link holds carries only the parameter arrays.)"""
    import copy
    return copy.deepcopy(template)


def _solve_step(solve_reform, baseline_arrays, base_dir, reform_dir, country):
    """Build the solve callable an experiment invokes as ``solve(ctx)``: ship the channels' parameter
    overrides (+ any staged mortality shock) to the OG runner and capture the reform solution."""
    def solve_step(ctx):
        ctx.reform_tpi = solve_reform(ctx.og_reform, baseline_arrays, ctx.extras.get("health_shock"),
                                      base_dir, reform_dir, country)
        return ctx.reform_tpi
    return solve_step


def run(experiment_fn, country, *, solve_reform, export_baseline=None,
        out_root="./oglink_runs", prebuilt=None) -> ExperimentContext:
    """Run one experiment. ``experiment_fn(ctx, solve)`` calls channels and calls solve(ctx) once.
    A ``prebuilt`` tuple (og_template, base_tpi, base_dir, baseline_arrays) reuses an already-exported
    baseline (the battery reuses one across reforms instead of re-exporting the identical baseline);
    otherwise ``export_baseline`` is required."""
    name = getattr(experiment_fn, "__name__", "experiment")
    ctx = ExperimentContext(country=country)
    reform_dir = os.path.join(out_root, name, "reform")
    if prebuilt is not None:
        template, ctx.base_tpi, base_dir, baseline_arrays = prebuilt
    elif export_baseline is not None:
        template, ctx.base_tpi, base_dir, baseline_arrays = export_baseline(country, out_root)
    else:
        raise ValueError("run() needs either prebuilt=(...) or export_baseline=callable")
    ctx.concordance = _load_concordance(base_dir)
    ctx.og_reform = _fresh_reform(template)
    experiment_fn(ctx, _solve_step(solve_reform, baseline_arrays, base_dir, reform_dir, country))
    return ctx


def run_across_steps(step_fns, country, *, export_baseline, solve_reform,
                     out_root="./oglink_runs") -> list:
    """Export the baseline ONCE, then one reform per CUMULATIVE step. ``step_fns`` is a list of
    (label, step_fn(ctx, solve)); each shares the baseline -- the layered 'what does each added channel
    do' view. A non-converging step is recorded and skipped, not fatal to the batch."""
    template, base_tpi, base_dir, baseline_arrays = export_baseline(country, out_root)
    concordance = _load_concordance(base_dir)
    results = []
    for label, step_fn in step_fns:
        ctx = ExperimentContext(country=country, base_tpi=base_tpi, concordance=concordance)
        ctx.og_reform = _fresh_reform(template)
        reform_dir = os.path.join(out_root, "across_steps", label)
        try:
            step_fn(ctx, _solve_step(solve_reform, baseline_arrays, base_dir, reform_dir, country))
        except Exception as e:  # noqa: BLE001 -- one non-converging step must not kill the whole batch
            print(f"[across_steps] step '{label}' did NOT solve: {type(e).__name__}: {e}")
            ctx.extras["error"] = f"{type(e).__name__}: {e}"
        results.append((label, ctx))
    return results


def preflight(active: list[str]) -> list[str]:
    """Advisory cross-channel guardrails for a set of active channel names (no solving). Surfaces
    double-counting and 'don't stack these' cautions; the orchestrator/CLI can print them before a run."""
    a = set(active)
    msgs: list[str] = []
    if "energy_price" in a and "carbon_tax" in a:
        msgs.append("energy_price + carbon_tax both wedge the energy good's tau_c -- a resource cost and "
                    "a tax are different objects; ensure the increase is not counted twice.")
    if {"carbon_tax", "emit_carbon_penalty"} & a:
        msgs.append("carbon price must appear ONCE: set it as policy feeding both sides (carbon_tax on OG, "
                    "emit_carbon_penalty on CLEWS); do not also infer a carbon price from a CLEWS dual into OG.")
    if "capital_intensity" in a and "investment" in a:
        msgs.append("capital_intensity (private generation capital share, gamma) and investment (PUBLIC "
                    "grid/T&D capex -> K_g) are COMPLEMENTARY, not double-counting: different capital, lever.")
    if "capital_intensity" in a and "energy_capex" in a:
        msgs.append("capital_intensity (gamma, factor share) and energy_capex (ITC, cost-of-capital) are TWO "
                    "mechanisms for the same buildout, OPPOSITE sign on energy K -- pick one, do NOT stack.")
    return msgs
