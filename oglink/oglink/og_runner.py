"""The OG-env runner: the ONLY module that imports ogcore + a country OG package. It ships in the link
repo but is EXECUTED BY the OG model's own interpreter --

    <env_python> -m oglink.og_runner export-baseline --og-package ogphl --out-dir ...
    <env_python> -m oglink.og_runner solve-reform   --baseline-dir ... --reform-dir ... --overrides ...

-- with PYTHONPATH pointing at the link source so this module (and the pure-python serde/_demog/health_pop/
progress it uses) import here, while ogcore + the country package come from the OG env. The
link never imports any of this. Boundary I/O is via serde (JSON in, .npz out); no ogcore object is ever
serialized (cloudpickle can pickle a Specifications but corrupts its paramtools validation schema on
reload), so the reform REBUILDS the baseline fresh instead of reloading one.

Two modes:
  export-baseline -- build the country baseline (generic via --og-package), solve it, and write the param
                     arrays + solution the link needs.
  solve-reform    -- rebuild the same baseline fresh, apply the link's parameter overrides (+ a health
                     mortality re-solve if present), solve the reform, write the reform solution.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib
import importlib.resources
import json
import os
import sys

import numpy as np

from . import health_pop, serde
from ._demog import baseline_pop
from .progress import solve_progress


@contextlib.contextmanager
def _client(num_workers):
    from distributed import Client
    if num_workers and num_workers > 1:
        c = Client(n_workers=num_workers, threads_per_worker=1, dashboard_address=None)
    else:
        c = Client(processes=False, dashboard_address=None)
    try:
        yield c
    finally:
        c.close()


def _sector_good_names(og_package, model_M, model_I):
    """Ordered industry (PROD_DICT) and good (CONS_DICT) group NAMES, for labeling figures by name
    instead of "sector k". Returned only when they line up with the model's realized M / I (a positional
    match -- the figures index by position); else None, so the viz falls back to numbered labels. Runs in
    the OG env (it imports the country package, which the link env can't); best-effort, never raises."""
    try:
        pkg = importlib.import_module(og_package)
        prod, cons = getattr(pkg, "PROD_DICT", None), getattr(pkg, "CONS_DICT", None)
        ind = list(prod) if prod and len(prod) == int(model_M) else None
        good = list(cons) if cons and len(cons) == int(model_I) else None
        return ind, good
    except Exception:  # noqa: BLE001 -- names are a labeling convenience; absence just means numbered labels
        return None, None


def _discover_concordance(og_package, model_M):
    """The energy-port concordance for this country, discovered from the package's own PROD_DICT/CONS_DICT
    (electricity must be an ISOLATED industry -- see contract.Concordance.from_dicts). Returned as a plain
    dict for export, because the link's env cannot import the country package to compute it. A
    single-industry (M<=1) baseline has no electricity industry, so it is unconditionally unavailable."""
    from dataclasses import asdict

    from .contract import Concordance

    if int(model_M) <= 1:
        why = f"{og_package} ran at M={int(model_M)} (no multisector calibration) -- no electricity industry"
        return {"energy_industry_index": None, "energy_good_index": None,
                "unavailable": {"energy_industry_index": why, "energy_good_index": why}}
    pkg = importlib.import_module(og_package)
    prod, cons = getattr(pkg, "PROD_DICT", None), getattr(pkg, "CONS_DICT", None)
    if prod is None or cons is None:
        why = f"{og_package} exposes no PROD_DICT/CONS_DICT to locate electricity"
        return {"energy_industry_index": None, "energy_good_index": None,
                "unavailable": {"energy_industry_index": why, "energy_good_index": why}}
    # The concordance index is a POSITIONAL offset into PROD_DICT; it only lines up with the model's
    # Z/gamma/io_matrix columns if the loaded calibration was built at this exact aggregation. Refuse to
    # emit a possibly-misaligned index when the group count disagrees with the baseline's realized M.
    if len(prod) != int(model_M):
        why = (f"{og_package} PROD_DICT has {len(prod)} groups but the baseline solved at M={int(model_M)} "
               "-- the aggregation the concordance is read from does not match the model's columns, so the "
               "energy-port indices would be misaligned")
        return {"energy_industry_index": None, "energy_good_index": None,
                "unavailable": {"energy_industry_index": why, "energy_good_index": why}}
    return asdict(Concordance.from_dicts(prod, cons))


def _read_solution(output_base, ss):
    from ogcore.utils import safe_read_pickle
    sub = ("SS", "SS_vars.pkl") if ss else ("TPI", "TPI_vars.pkl")
    return safe_read_pickle(os.path.join(output_base, *sub))


def _load_calibration(p, og_package, params_resource, calibration):
    """Load the single-industry DEFAULT + (optional) multisector OVERLAY into ``p`` -- the country's own
    load order. The overlay sets M/I + sector arrays but inherits scalars (e.g. initial_Kg_ratio) from the
    default, so it must be applied ON TOP of the default (loading it standalone fails paramtools)."""
    with importlib.resources.open_text(og_package, params_resource) as f:
        p.update_specifications(json.load(f))
    if calibration:
        with importlib.resources.open_text(og_package, calibration) as f:
            p.update_specifications(json.load(f))
    # Every SS solve uses the Anderson root method. Applied here so all three Specifications sites
    # (baseline, continuation step, reform) inherit it; caller overrides applied later still win.
    p.update_specifications({"SS_root_method": "anderson"})


def _update_demographics(p, un_code, cache_dir):
    """Refresh demographics the SAME way every OG model does -- ogcore.demographics, which fetches from the
    UN data portal and falls back to the github EAPD-DRB/Population-Data repo (inside get_un_data) -- and
    FAIL SAFELY to the country's BUILT-IN baked demographics (already loaded from its calibration JSON,
    still in ``p``) when the live data is unavailable. The link NEVER substitutes its own copy. Country-
    generic: the only country-specific input is ``un_code`` (the package's UN_COUNTRY_CODE). Sets
    ``p._demog_spec`` (the fetched overlay the continuation re-applies, or None when built-in) and
    ``p._pop_aux`` (the rate aux the health channel needs, or None when built-in -> the shock skips)."""
    import io

    guard = sys.stdin
    sys.stdin = io.StringIO("")     # ogcore's get_un_data input()-prompts for a UN token; EOF -> github backup
    try:
        pop = baseline_pop(p, un_country_code=un_code,
                           download_path=os.path.join(cache_dir, "_demog_cache"))
        p.update_specifications(pop[0])
        p._demog_spec = pop[0]
        p._pop_aux = {"pop_dist": pop[1], "pre_pop_dist": pop[2], "fert_rates": pop[3],
                      "mort_rates": pop[4], "infmort_rates": pop[5], "imm_rates": pop[6]}
        print(f"[og_runner] demographics: live update applied (UN portal -> github backup) for country "
              f"{un_code}", file=sys.stderr)
    except Exception as e:          # noqa: BLE001 -- portal+github unavailable -> use the country's built-in
        p._demog_spec = None        # keep the JSON-baked demographics already in p (do NOT override)
        p._pop_aux = None           # no rate aux -> the health mortality shock skips; baseline still solves
        print(f"[og_runner] demographics: live update unavailable ({type(e).__name__}: {str(e)[:120]}); "
              f"using country {un_code}'s BUILT-IN calibrated demographics (health shock will skip)",
              file=sys.stderr)
    finally:
        sys.stdin = guard


def _build_baseline_specs(og_package, params_resource, og_start_year, num_workers, out_dir,
                          calibration=None, demog_override=None):
    """Build the country baseline by LOADING the country model's OWN calibration -- the link no longer
    authors any aggregation or sector factors. Load the single-industry DEFAULT (``params_resource``) as
    the base, then OVERLAY the chosen multisector ``calibration`` if any. Country packages ship their
    multisector JSON as an update_specifications OVERLAY on the default: it sets M/I + the sector arrays
    but INHERITS scalars (e.g. initial_Kg_ratio) from the default, so loading it standalone fails
    paramtools cross-validation (e.g. gamma_g>0 requires initial_Kg_ratio>0). This mirrors the country's
    own multi-industry calibrated load order. When ``calibration`` is None
    the baseline stays single-industry (the energy channels skip). Demographics are UPDATED via the
    country's own mechanism (ogcore.demographics: UN portal -> github backup -> the country's built-in
    JSON), never the link's own copy; the UN code is the package's own (ogphl.UN_COUNTRY_CODE). A reform
    passes ``demog_override`` -- the baseline's saved ``(demog_spec, pop_aux)`` -- to INHERIT the baseline's
    exact demographics (persist+load) instead of re-fetching (see solve_reform)."""
    from ogcore.parameters import Specifications

    pkg = importlib.import_module(og_package)
    un_code = str(getattr(pkg, "UN_COUNTRY_CODE", "") or "")
    if not un_code:
        raise ValueError(f"{og_package} does not expose UN_COUNTRY_CODE; the demographic build needs it.")
    os.makedirs(out_dir, exist_ok=True)
    p = Specifications(baseline=True, num_workers=num_workers, baseline_dir=out_dir, output_base=out_dir)
    _load_calibration(p, og_package, params_resource, calibration)
    kind = (f"{params_resource} + {calibration} overlay" if calibration
            else f"{params_resource} (single-industry -> energy channels skip)")
    print(f"[og_runner] {og_package}: loaded {kind} (M={p.M}, I={p.I})", file=sys.stderr)
    p._un_code = un_code
    if demog_override is None:
        # BASELINE (or a reform whose baseline predates demographic persistence): fetch once via the
        # country's own mechanism, caching under out_dir/_demog_cache.
        _update_demographics(p, un_code, out_dir)
    else:
        # REFORM inherits the baseline's demographics (persist+load): re-apply the baseline's EXACT saved
        # overlay -- NO re-fetch -- so reform-vs-baseline omega is identical and differs ONLY by the
        # reform's channels. demog_override = (spec, aux); both are None when the baseline used its
        # BUILT-IN demographics (leave the JSON-baked values; the health mortality shock then skips).
        spec, aux = demog_override
        if spec is not None:
            p.update_specifications(spec)
        p._demog_spec = spec
        p._pop_aux = aux
        msg = ("INHERITED from baseline (no re-fetch)" if spec is not None
               else "INHERITED baseline's BUILT-IN (no re-fetch; health shock will skip)")
        print(f"[og_runner] demographics: {msg} for country {un_code}", file=sys.stderr)
    if int(getattr(p, "start_year", og_start_year)) != og_start_year:
        print(f"[og_runner] WARNING: OG start_year {p.start_year} != scenario og_start_year {og_start_year}; "
              "CLEWS year-alignment will be off.", file=sys.stderr)
    return p


def _solve(p, num_workers, ss, show_progress, label):
    from ogcore.execute import runner
    with _client(num_workers) as client, \
            solve_progress(getattr(p, "mindist_TPI", 1e-5), label, enabled=show_progress):
        runner(p, time_path=not ss, client=client)
    out = _read_solution(p.output_base, ss)
    if float(getattr(p, "RC_SS", 1e-8)) > 1e-8:
        with contextlib.suppress(Exception):
            from ogcore.utils import safe_read_pickle
            ss_vars = safe_read_pickle(os.path.join(p.output_base, "SS", "SS_vars.pkl"))
            rc = ss_vars.get("resource_constraint_error") if isinstance(ss_vars, dict) else None
            if rc is not None:
                print(f"[og_runner] {label}: RC_SS gate loosened to {float(p.RC_SS):.0e}; realized SS "
                      f"max|RC|={np.max(np.abs(np.atleast_1d(rc))):.2e}", file=sys.stderr)
    return out


# max-min spread of the per-industry capital share above which OG-Core's cold SS solve is unreliable
# (it seeds every industry price at p_m=1, which is wrong when capital shares -- hence relative prices --
# differ a lot) and we solve by continuation instead.
_GAMMA_DISPERSION_THRESHOLD = 0.05

# max |reform gamma - baseline gamma| above which a reform's COLD SS solve is unreliable (the same p_m=1
# seed problem as the baseline, now triggered by a channel shifting an industry's capital share a lot --
# e.g. capital_intensity on PHL M=8 pushes electricity gamma 0.78->0.88, which cold-diverges to NaN). Such
# a reform is solved by continuation from the (already-solved) baseline SS instead.
_REFORM_GAMMA_CONT_THRESHOLD = 0.02


def _validate_ss(out_dir):
    """Sanity-check a solved steady state (mirrors a country example's validate_ss): every industry price
    positive, numeraire p_m[-1]=1, r in (0,0.2), K/Y in (1,8). A guard for the cold-solve path; the real
    protection against a spurious root is solving heterogeneous-gamma calibrations by continuation."""
    from ogcore.utils import safe_read_pickle
    try:
        ss = safe_read_pickle(os.path.join(out_dir, "SS", "SS_vars.pkl"))
        s = lambda x: float(np.squeeze(x))
        p_m = np.atleast_1d(np.squeeze(ss["p_m"]))
        r, K, Y = s(ss["r"]), s(ss["K"]), s(ss["Y"])
        return bool((p_m > 0).all() and np.isclose(p_m[-1], 1.0, atol=1e-3)
                    and 0.0 < r < 0.2 and 1.0 < K / Y < 8.0)
    except Exception:                                                            # noqa: BLE001
        return False


def _continuation_baseline(og_package, params_resource, calibration, num_workers, out_dir, p_final,
                           ss, show_progress):
    """Solve the calibrated baseline steady state by adaptive CONTINUATION (homotopy), then run the TPI off
    it -- a generic robust solver, NOT a country-specific build, so it needs no change to the OG repo. We
    cold-solve a flat-gamma / Z=1 anchor (where OG-Core's p_m=1 guess is correct), then morph gamma+Z to
    the calibrated values in adaptive warm-started steps (the cross-industry dispersion is what moves the
    relative prices, so we walk it in). The arithmetic-mean anchor holds the aggregate capital share fixed
    and only grows the dispersion. If the path stalls we RAISE -- the link can't solve this calibration, so
    the caller fails loudly rather than shipping a wrong equilibrium. SS reused for the TPI (a cold re-solve
    would diverge), exactly as the country examples do. Writes SS/TPI/model_params under out_dir."""
    import pickle
    import shutil

    import cloudpickle
    from ogcore import TPI
    from ogcore.execute import runner

    gamma_target = np.asarray(p_final.gamma, dtype=float).ravel()
    Z_arr = np.asarray(p_final.Z, dtype=float)
    Z_target = Z_arr[-1].ravel() if Z_arr.ndim == 2 else Z_arr.ravel()
    M = int(p_final.M)
    anchor_gamma = np.full(M, float(gamma_target.mean()))      # flat share -> p_m=1 holds -> cold-solvable
    anchor_Z = np.ones(M)

    def build_step(gamma, Z, baseline, output_base, baseline_dir=None):
        from ogcore.parameters import Specifications
        p = Specifications(baseline=baseline, num_workers=num_workers,
                           baseline_dir=baseline_dir or output_base, output_base=output_base)
        _load_calibration(p, og_package, params_resource, calibration)
        if p_final._demog_spec is not None:                    # fetched demographics (else the JSON's stand)
            p.update_specifications(p_final._demog_spec)       # reused, no re-fetch per step
        p.update_specifications({"gamma": list(gamma), "Z": [list(Z)]})
        return p

    work = os.path.join(out_dir, "_continuation")
    if os.path.exists(work):
        shutil.rmtree(work)
    anchor_dir = os.path.join(work, "anchor")
    os.makedirs(os.path.join(anchor_dir, "SS"), exist_ok=True)
    print(f"[og_runner] baseline: heterogeneous gamma (spread {gamma_target.max()-gamma_target.min():.2f}) "
          f"-> solving SS by continuation (M={M})", file=sys.stderr)
    with _client(num_workers) as client:
        with solve_progress(1e-5, "baseline:anchor", enabled=show_progress):
            runner(build_step(anchor_gamma, anchor_Z, True, anchor_dir), time_path=False, client=client)
        good_dir, t, dt, idx = anchor_dir, 0.0, 0.125, 0
        while t < 1.0 - 1e-9:
            t_try = min(t + dt, 1.0)
            gamma = (1 - t_try) * anchor_gamma + t_try * gamma_target
            Z = (1 - t_try) * anchor_Z + t_try * Z_target
            idx += 1
            step_dir = os.path.join(work, f"t{idx}")
            os.makedirs(os.path.join(step_dir, "SS"), exist_ok=True)
            try:
                runner(build_step(gamma, Z, False, step_dir, baseline_dir=good_dir),
                       time_path=False, client=client)
                t, good_dir, dt = t_try, step_dir, min(dt * 1.5, 0.25)
                print(f"[og_runner]   continuation t={t:.3f} (dt={dt:.3f}) solved", file=sys.stderr)
            except Exception:                                  # noqa: BLE001 -- step failed; shrink + retry
                dt /= 2.0
                if dt < 0.01:
                    raise RuntimeError(
                        f"baseline continuation stalled at t={t:.3f} (dt<0.01) for {og_package}: the "
                        "calibrated steady state could not be reached; this country cannot be coupled "
                        "until its baseline is solvable.")
    # place the converged calibrated SS as the baseline SS, then run the TPI off it (a cold re-solve of
    # the calibrated SS would diverge), mirroring the country examples' run_baseline_tpi.
    os.makedirs(os.path.join(out_dir, "SS"), exist_ok=True)
    shutil.copyfile(os.path.join(good_dir, "SS", "SS_vars.pkl"),
                    os.path.join(out_dir, "SS", "SS_vars.pkl"))
    p_base = build_step(gamma_target, Z_target, True, out_dir)
    with open(os.path.join(out_dir, "model_params.pkl"), "wb") as f:
        cloudpickle.dump(p_base, f)
    if ss:
        return _read_solution(out_dir, ss=True)
    with _client(num_workers) as client, solve_progress(getattr(p_base, "mindist_TPI", 1e-5),
                                                        "baseline:TPI", enabled=show_progress):
        tpi_out = TPI.run_TPI(p_base, client=client)
    os.makedirs(os.path.join(out_dir, "TPI"), exist_ok=True)
    with open(os.path.join(out_dir, "TPI", "TPI_vars.pkl"), "wb") as f:
        pickle.dump(tpi_out, f)
    return _read_solution(out_dir, ss=False)


def _continuation_reform(a, gamma_base, overrides, demog_spec, ss, show_progress):
    """Solve a reform whose GAMMA shift is large by CONTINUATION from the already-solved baseline SS, then
    run the reform TPI off it. A cold reform solve seeds p_m=1 (wrong when an industry's capital share is
    high), so a big gamma move diverges to NaN (PHL M=8 electricity gamma 0.78->0.88). The baseline
    (gamma_base) is solved at a.baseline_dir; we morph gamma to the reform value in adaptive warm-started
    steps, holding the NON-gamma overrides at their reform values throughout. Mirrors
    _continuation_baseline, anchored at the baseline SS rather than a flat-gamma anchor. Returns the
    consumed solution dict; RAISES if the path stalls (then the reform gamma is genuinely unreachable)."""
    import pickle
    import shutil

    import cloudpickle
    from ogcore import TPI
    from ogcore.execute import runner
    from ogcore.parameters import Specifications

    gamma_base = np.asarray(gamma_base, dtype=float).ravel()
    gamma_reform = np.asarray(overrides["gamma"], dtype=float).ravel()

    def build_step(gamma, output_base, baseline_dir):
        p = Specifications(baseline=False, num_workers=a.num_workers,
                           baseline_dir=baseline_dir, output_base=output_base)
        _load_calibration(p, a.og_package, a.params_resource, a.calibration)
        if demog_spec is not None:                       # reuse the fetched demographics (no UN re-fetch)
            p.update_specifications(demog_spec)
        for name, value in overrides.items():            # all reform overrides at full value ...
            setattr(p, name, value)
        p.gamma = np.asarray(gamma, dtype=float)         # ... except gamma, which we walk in
        p.__dict__.pop("_e_long_cache", None)
        return p

    work = os.path.join(a.reform_dir, "_continuation")
    if os.path.exists(work):
        shutil.rmtree(work)
    print(f"[og_runner] reform: gamma shift {float(np.max(np.abs(gamma_reform - gamma_base))):.2f} "
          "-> solving SS by continuation from the baseline", file=sys.stderr)
    with _client(a.num_workers) as client:
        good_dir, t, dt, idx = a.baseline_dir, 0.0, 0.125, 0
        while t < 1.0 - 1e-9:
            t_try = min(t + dt, 1.0)
            gamma = (1 - t_try) * gamma_base + t_try * gamma_reform
            idx += 1
            step_dir = os.path.join(work, f"t{idx}")
            os.makedirs(os.path.join(step_dir, "SS"), exist_ok=True)
            try:
                runner(build_step(gamma, step_dir, good_dir), time_path=False, client=client)
                t, good_dir, dt = t_try, step_dir, min(dt * 1.5, 0.25)
                print(f"[og_runner]   reform continuation t={t:.3f} (dt={dt:.3f}) solved", file=sys.stderr)
            except Exception:                            # noqa: BLE001 -- step failed; shrink + retry
                dt /= 2.0
                if dt < 0.01:
                    raise RuntimeError(
                        f"reform gamma continuation stalled at t={t:.3f} (dt<0.01): the reform steady "
                        "state could not be reached -- the requested capital share may be infeasible.")
    os.makedirs(os.path.join(a.reform_dir, "SS"), exist_ok=True)
    shutil.copyfile(os.path.join(good_dir, "SS", "SS_vars.pkl"),
                    os.path.join(a.reform_dir, "SS", "SS_vars.pkl"))
    r_final = build_step(gamma_reform, a.reform_dir, a.baseline_dir)   # full reform; SS read from reform_dir
    # A large gamma shift makes this the hardest reform to converge. Its transition
    # path limit-cycles at the multisector calibration's nu=0.2 (observed: TPIdist plateaus ~0.86, never
    # reaching mindist). Damp the TPI update harder than the calibration default and grant more iterations
    # so the more-damped (slower) path has room to settle. Scoped to the continuation reform only.
    r_final.nu = min(float(getattr(r_final, "nu", 0.2)), 0.1)
    r_final.maxiter = max(int(getattr(r_final, "maxiter", 250)), 500)
    with open(os.path.join(a.reform_dir, "model_params.pkl"), "wb") as f:
        cloudpickle.dump(r_final, f)
    if ss:
        return _read_solution(a.reform_dir, ss=True)
    with _client(a.num_workers) as client, solve_progress(getattr(r_final, "mindist_TPI", 1e-5),
                                                          "reform:TPI", enabled=show_progress):
        tpi_out = TPI.run_TPI(r_final, client=client)
    os.makedirs(os.path.join(a.reform_dir, "TPI"), exist_ok=True)
    with open(os.path.join(a.reform_dir, "TPI", "TPI_vars.pkl"), "wb") as f:
        pickle.dump(tpi_out, f)
    return _read_solution(a.reform_dir, ss=False)


def _solve_baseline(og_package, params_resource, og_start_year, num_workers, out_dir, calibration,
                    ss, show_progress):
    """Build + SOLVE the country baseline, choosing a solve strategy by the calibration's gamma dispersion.
    Single-industry / flat-gamma calibrations cold-solve reliably (OG-Core's runner). A multisector
    calibration with heterogeneous capital shares does NOT cold-solve (OG-Core's p_m=1 guess is wrong), so
    it is solved by continuation; a cold solve that fails validation also falls back to continuation. If
    the continuation stalls it raises (fail loud, never ship a wrong equilibrium). Returns (p, solution)."""
    p = _build_baseline_specs(og_package, params_resource, og_start_year, num_workers, out_dir, calibration)
    gamma = np.asarray(p.gamma, dtype=float).ravel()
    dispersion = float(gamma.max() - gamma.min()) if gamma.size else 0.0
    if int(p.M) <= 1 or dispersion <= _GAMMA_DISPERSION_THRESHOLD:
        sol = _solve(p, num_workers, ss, show_progress, "baseline")
        if _validate_ss(out_dir):
            return p, sol
        print("[og_runner] baseline cold solve failed SS validation; retrying by continuation",
              file=sys.stderr)
    sol = _continuation_baseline(og_package, params_resource, calibration, num_workers, out_dir, p,
                                 ss, show_progress)
    return p, sol


def _apply_health(p, health):
    """Port of Runtime.apply_health_shock: the signed-target disease_pop re-solve, RC_SS loosened ONLY
    for the lives-saved (excess_deaths<0) direction. Runs here because it needs a real Specifications +
    ogcore.demographics."""
    aux = getattr(p, "_pop_aux", None)
    if aux is None or "excess_deaths" not in health:
        print("[og_runner] health spec without pop aux / excess_deaths; skipping mortality shock",
              file=sys.stderr)
        return p
    p.__dict__.pop("_e_long_cache", None)
    target = float(health["excess_deaths"])
    profile = np.asarray(health["profile"], dtype=float)
    ny = int(health.get("phase_years", 5))
    un = getattr(p, "_un_code", None)
    if not un:   # _build_baseline_specs always sets it; a bare Specifications must not silently get PHL's
        raise ValueError("health shock: Specifications lacks _un_code (the country's UN code); build the "
                         "baseline via _build_baseline_specs so demographics know which country this is.")
    if target < 0:
        p.RC_SS = float(health.get("rc_ss", 1e-6))
    pop_dict, scale = health_pop.disease_pop(p, aux, target, profile, phase_years=ny, un_country_code=un)
    print(f"[og_runner] disease_pop: excess_deaths target {target:+,.0f} -> shock_scale {scale:+.5g}",
          file=sys.stderr)
    p.update_specifications(pop_dict)
    return p


# --- in-process framework callables (OG env only) --------------------------------
# Same contract as runtime.export_baseline / solve_reform, but solving IN THIS PROCESS (no subprocess).
# For scripts that already run under the OG model's interpreter and want OG-Core's native plotting too
# (e.g. run_across_steps' full deck). framework.run works with either pair injected.

def inprocess_callables(og_package, params_resource, og_start_year, *,
                        num_workers=7, show_progress=False, ss=False, calibration=None):
    """Return (export_baseline, solve_reform) closures that build/solve in-process via ogcore.
    ``calibration`` is the chosen multisector param resource (None -> single-industry default)."""
    def export_baseline(country, out_root):
        base_dir = os.path.join(out_root, "baseline")
        p, base = _solve_baseline(og_package, params_resource, og_start_year,
                                  num_workers, base_dir, calibration, ss, show_progress)
        # Export the discovered concordance next to the baseline (same file the subprocess path writes),
        # so framework._load_concordance + the viz driver find the run's energy ports either way.
        _ind, _good = _sector_good_names(og_package, p.M, p.I)
        with open(os.path.join(base_dir, "baseline_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"schema_version": serde.BASELINE_META_SCHEMA,
                       "og_package": og_package, "M": int(p.M), "I": int(p.I),
                       "industry_names": _ind, "good_names": _good,
                       "concordance": _discover_concordance(og_package, p.M)}, f)
        return p, base, base_dir, {}        # template = real Specifications; baseline_arrays unused here

    def solve_reform(og_reform, baseline_arrays, health_shock, base_dir, reform_dir, country):
        og_reform.baseline = False
        og_reform.baseline_dir = base_dir
        og_reform.output_base = reform_dir
        og_reform.__dict__.pop("_e_long_cache", None)
        os.makedirs(reform_dir, exist_ok=True)
        if health_shock is not None:
            og_reform = _apply_health(og_reform, health_shock)
        return _solve(og_reform, num_workers, ss, show_progress, "reform")

    return export_baseline, solve_reform


# --- subprocess modes (invoked by the link via the CLI) --------------------------

def export_baseline(a):
    p, sol = _solve_baseline(a.og_package, a.params_resource, a.og_start_year,
                             a.num_workers, a.out_dir, a.calibration, a.ss, not a.no_progress)
    serde.save_params_npz(os.path.join(a.out_dir, "baseline_params.npz"), p)
    serde.save_solution_npz(os.path.join(a.out_dir, "baseline_solution.npz"), sol)
    if not a.ss:   # a TPI solve also wrote SS_vars; export the SS slice so SS-mode reforms compare SS->SS
        with contextlib.suppress(Exception):
            serde.save_solution_npz(os.path.join(a.out_dir, "baseline_solution_ss.npz"),
                                    _read_solution(a.out_dir, ss=True))
    # Persist the baseline's fetched demographics so a reform INHERITS them (persist+load) rather than
    # re-fetching: ogcore's get_pop_objs always re-downloads (download_path is a write-sink), so a shared
    # cache dir would neither avoid a fetch nor guarantee identical data -- the saved overlay does.
    serde.save_demographics_npz(os.path.join(a.out_dir, "baseline_demographics.npz"),
                                getattr(p, "_demog_spec", None), getattr(p, "_pop_aux", None))
    # NB: we do NOT pickle the baseline Specifications. cloudpickle can serialize it but CORRUPTS
    # paramtools' validation schema on reload (update_specifications then fails), which the reform's
    # health re-solve needs. solve-reform rebuilds a FRESH baseline instead (deterministic, clean
    # paramtools state) and points baseline_dir at the solved solution written here.
    import ogcore
    # The energy-port concordance is discovered in the OG env (it needs the country package's PROD_DICT/
    # CONS_DICT, which the link env can't import) and EXPORTED here for the link to read -- tied to the
    # baseline's realized M, so a single-industry baseline reports the ports unavailable (channels skip).
    _ind, _good = _sector_good_names(a.og_package, p.M, p.I)   # figures label sectors/goods by name
    meta = {"schema_version": serde.BASELINE_META_SCHEMA,
            "og_package": a.og_package, "un_code": getattr(p, "_un_code", ""), "M": int(p.M), "I": int(p.I),
            "S": int(p.S), "start_year": int(getattr(p, "start_year", a.og_start_year)),
            "industry_names": _ind, "good_names": _good,
            "ogcore_version": getattr(ogcore, "__version__", None), "ss_only": bool(a.ss),
            "concordance": _discover_concordance(a.og_package, p.M)}
    with open(os.path.join(a.out_dir, "baseline_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f)
    print(f"[og_runner] exported baseline -> {a.out_dir}", file=sys.stderr)


def solve_reform(a):
    # Rebuild the baseline Specifications FRESH (deterministic; same calibration the export solved) rather
    # than reloading a pickle -- a fresh object has clean paramtools state, so the health re-solve's
    # update_specifications works (a cloudpickled one's doesn't). baseline_dir points at the solved
    # baseline solution on disk, which OG-Core reads for the reform.
    # REFORM inherits the baseline's demographics (persist+load): load the EXACT population overlay the
    # baseline fetched+applied and pass it as demog_override so the reform re-applies it WITHOUT a fetch.
    # (ogcore's get_pop_objs treats download_path as a write-sink and always re-fetches, so sharing a
    # cache dir would neither avoid a second fetch nor guarantee identical data.) File absent -> a
    # baseline solved before persistence -> fall back to the fetch, preserving the old behavior.
    demog_override = serde.load_demographics_npz(os.path.join(a.baseline_dir, "baseline_demographics.npz"))
    r = _build_baseline_specs(a.og_package, a.params_resource, a.og_start_year,
                              a.num_workers, a.reform_dir, calibration=a.calibration,
                              demog_override=demog_override)
    gamma_base = np.array(r.gamma, dtype=float)  # calibrated baseline gamma, BEFORE any channel override
    demog_spec = getattr(r, "_demog_spec", None)
    r.baseline = False
    r.baseline_dir = a.baseline_dir
    r.output_base = a.reform_dir
    # Apply the channel overrides by DIRECT attribute assignment -- exactly what the channels do
    # in-process (p.tau_c = ..., p.alpha_I = ..., p.e = ...). Routing them through update_specifications
    # re-runs paramtools validation that direct assignment never triggers (it rejects the full morbidity
    # e array); OG-Core's solver reads these numpy attributes directly, so setattr reproduces the old
    # in-process semantics exactly.
    overrides = serde.read_overrides_json(a.overrides)
    for name, value in overrides.items():
        setattr(r, name, value)
    r.__dict__.pop("_e_long_cache", None)        # e may have been replaced; drop ogcore's memoized long-e
    has_health = bool(a.health_shock and os.path.exists(a.health_shock))
    if has_health:
        r = _apply_health(r, serde.read_health_json(a.health_shock))
    # A large gamma shift cold-diverges (OG-Core seeds p_m=1, wrong for a high capital share), so solve
    # such a reform by continuation from the already-solved baseline SS. Only gamma-shifting channels
    # (capital_intensity) trip this; Z/tau_c reforms cold-solve fine. Not combined with a health shock.
    big_gamma = ("gamma" in overrides and not has_health and float(np.max(np.abs(
        np.asarray(overrides["gamma"], dtype=float).ravel() - gamma_base.ravel()))) > _REFORM_GAMMA_CONT_THRESHOLD)
    if big_gamma:
        sol = _continuation_reform(a, gamma_base, overrides, demog_spec, a.ss, not a.no_progress)
    else:
        sol = _solve(r, a.num_workers, a.ss, not a.no_progress, "reform")
    serde.save_solution_npz(os.path.join(a.reform_dir, "reform_solution.npz"), sol)
    print(f"[og_runner] solved reform -> {a.reform_dir}", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="oglink.og_runner")
    sub = ap.add_subparsers(dest="mode", required=True)

    e = sub.add_parser("export-baseline")
    e.add_argument("--og-package", required=True)
    e.add_argument("--params-resource", required=True,
                   help="the package's single-industry default params (loaded when no --calibration is chosen)")
    e.add_argument("--calibration", default=None,
                   help="chosen multisector param resource (from discovery); omit for single-industry")
    e.add_argument("--og-start-year", type=int, required=True)
    e.add_argument("--num-workers", type=int, default=1)
    e.add_argument("--out-dir", required=True)
    e.add_argument("--ss", action="store_true")
    e.add_argument("--no-progress", action="store_true")
    e.set_defaults(func=export_baseline)

    s = sub.add_parser("solve-reform")
    s.add_argument("--baseline-dir", required=True)
    s.add_argument("--reform-dir", required=True)
    s.add_argument("--overrides", required=True)
    s.add_argument("--health-shock", default=None)
    s.add_argument("--num-workers", type=int, default=1)
    # the reform rebuilds the baseline fresh (clean paramtools state), so it needs the same build inputs:
    s.add_argument("--og-package", required=True)
    s.add_argument("--params-resource", required=True)
    s.add_argument("--calibration", default=None,
                   help="MUST match the calibration the baseline was exported with (fresh rebuild)")
    s.add_argument("--og-start-year", type=int, required=True)
    s.add_argument("--ss", action="store_true")
    s.add_argument("--no-progress", action="store_true")
    s.set_defaults(func=solve_reform)

    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
