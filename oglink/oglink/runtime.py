"""The link-side run orchestrator. numpy/stdlib only -- it imports NO ogcore and NO country package.
To solve, it looks up the country's OG model in the registry and drives that model's OWN interpreter as
a subprocess (oglink.og_runner), handing over data files (JSON overrides in, .npz solutions out).
The link and the OG model stay in separate, independently-installed environments.

  export_baseline(country) -> (og_reform template, base_tpi, baseline_dir, baseline_arrays)
  solve_reform(og_reform, baseline_arrays, health_shock, base_dir, reform_dir, country) -> reform_tpi

These are injected into framework.run (replacing the old in-process build/solve/apply_health). The
baseline export is content-addressed + cached, so a battery of reforms re-uses one solved baseline.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass

from . import registry, serde

# Env isolation: oglink is installed into BOTH environments -- the link env (numpy/pandas only) and each
# OG model's env (which also has ogcore). The OG subprocess imports oglink.og_runner from its OWN
# site-packages, using its OWN numpy; we do NOT inject the link env's path onto the child (that would let
# the OG solve import the link env's numpy/scipy, defeating the no-pickle env separation the serde
# boundary exists to guarantee). og_runner sits unused in the link env -- ogcore is imported lazily, so it
# never triggers there.


@dataclass
class RunnerConfig:
    num_workers: int = 1
    show_progress: bool = True
    ss: bool = False                 # steady-state-only solve (fast; for the SS smoke / ss_smoke battery)
    registry_path: str | None = None
    rebuild: bool = False            # force a fresh baseline solve, ignoring any cached one (e.g. to pick
                                     # up newer UN demographics or a re-baked calibration)


def _run(entry, args, label, log_path=None):
    """Subprocess the OG runner, streaming its combined output LIVE to the parent's stderr and -- when
    ``log_path`` is given -- to a persisted per-run ``solve.log``. So a solve that FAILS or is KILLED
    always leaves a durable trail to trace back what happened (the old capture-then-dump lost everything
    on a SIGKILL). ``PYTHONUNBUFFERED`` keeps the last lines from being swallowed by buffering on a kill.
    Raises (naming the log) on a non-zero exit."""
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"      # make the CHILD emit UTF-8 (else Windows encodes stdout as cp1252)
    if log_path:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logf = open(log_path, "w", encoding="utf-8") if log_path else None
    try:
        # Pin BOTH ends to UTF-8: PYTHONIOENCODING (above) makes the child ENCODE stdout as UTF-8, and
        # encoding= makes THIS parent DECODE it as UTF-8 -- otherwise on Windows the child would write
        # cp1252 and the parent mis-read it. errors="replace" guarantees an odd byte can never abort an
        # otherwise-successful solve mid-stream.
        proc = subprocess.Popen([entry.env_python, "-m", "oglink.og_runner", *args], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                                encoding="utf-8", errors="replace")
        for line in proc.stdout:                           # surface runner diagnostics (progress, RC_SS) live
            sys.stderr.write(line)
            if logf:
                logf.write(line)
                logf.flush()
        rc = proc.wait()
    finally:
        if logf:
            logf.close()
    if rc != 0:
        where = f" Solve log: {log_path}" if log_path else " See stderr above."
        raise RuntimeError(f"og_runner {label} failed (exit {rc}) in the {entry.package} "
                           f"env [{entry.env_python}].{where}")
    return rc


def _cache_dir(out_root, entry, country, cfg):
    # the baseline is per-OG-model + scenario-independent; key the cache by the model + version + the
    # CHOSEN calibration, so switching calibrations (e.g. single-industry <-> multisector) never reuses
    # a baseline solved at a different aggregation.
    cal = os.path.splitext(entry.calibration)[0] if entry.calibration else "default"
    tag = f"{entry.key}-{entry.version or 'na'}-{cal}" + ("-ss" if cfg.ss else "")
    return os.path.join(out_root, "_og_baseline_cache", tag)


def _cache_current(cache, params_npz):
    """A cached baseline is reusable only if its params .npz exists AND its baseline_meta.json is at the
    CURRENT schema (carrying the discovered concordance). A meta written by an older link (no
    schema_version / no "concordance") is a MISS -- reusing it would silently make every energy channel
    skip on a baseline that may actually be energy-capable. The cache tag keys on the OG-package version,
    which does NOT change when the link's discovery logic changes, so this contract check is what
    invalidates a stale cache."""
    meta_path = os.path.join(cache, "baseline_meta.json")
    if not (os.path.exists(params_npz) and os.path.exists(meta_path)):
        return False
    try:
        with open(meta_path, encoding="utf-8-sig") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return False
    return int(meta.get("schema_version", 0)) >= serde.BASELINE_META_SCHEMA and "concordance" in meta


def export_baseline(country, out_root="./oglink_runs", cfg: RunnerConfig | None = None):
    """Ensure a solved baseline exists for ``country`` (subprocess the OG runner if not cached), then load
    its exported params + solution. Returns (OGParams template, base_tpi, baseline_dir, baseline_arrays)."""
    cfg = cfg or RunnerConfig()
    entry = registry.lookup(country, path=cfg.registry_path)         # fail-fast before any subprocess
    cache = _cache_dir(out_root, entry, country, cfg)
    params_npz = os.path.join(cache, "baseline_params.npz")
    solution_npz = os.path.join(cache, "baseline_solution.npz")
    if cfg.rebuild or not _cache_current(cache, params_npz):
        os.makedirs(cache, exist_ok=True)
        args = ["export-baseline", "--og-package", entry.package,
                "--params-resource", entry.params_resource_name,
                "--og-start-year", str(country.scenario.og_start_year),
                "--num-workers", str(cfg.num_workers), "--out-dir", cache]
        if entry.calibration:           # the chosen multisector calibration (else single-industry default)
            args += ["--calibration", entry.calibration]
        if cfg.ss:
            args.append("--ss")
        if not cfg.show_progress:
            args.append("--no-progress")
        _run(entry, args, "export-baseline", log_path=os.path.join(cache, "solve.log"))
    og, base_tpi, baseline_arrays = serde.load_baseline_bundle(params_npz, solution_npz)
    return og, base_tpi, cache, baseline_arrays


def solve_reform(og_reform, baseline_arrays, health_shock, base_dir, reform_dir, country,
                 cfg: RunnerConfig | None = None):
    """Serialize the channels' parameter overrides (+ a health shock if any), subprocess the OG runner to
    solve the reform in the OG env, and load the reform solution back. Returns reform_tpi (a dict)."""
    cfg = cfg or RunnerConfig()
    entry = registry.lookup(country, path=cfg.registry_path)
    os.makedirs(reform_dir, exist_ok=True)
    overrides = os.path.join(reform_dir, "reform_overrides.json")
    serde.write_overrides_json(serde.diff_against_baseline(og_reform, baseline_arrays), overrides)
    args = ["solve-reform", "--baseline-dir", base_dir, "--reform-dir", reform_dir,
            "--overrides", overrides, "--num-workers", str(cfg.num_workers),
            # the reform rebuilds the baseline fresh, so pass the same build inputs as export-baseline:
            "--og-package", entry.package, "--params-resource", entry.params_resource_name,
            "--og-start-year", str(country.scenario.og_start_year)]
    if entry.calibration:               # MUST match export-baseline's calibration (fresh rebuild)
        args += ["--calibration", entry.calibration]
    if health_shock is not None:
        hpath = os.path.join(reform_dir, "health.json")
        serde.write_health_json(health_shock, hpath)
        args += ["--health-shock", hpath]
    if cfg.ss:
        args.append("--ss")
    if not cfg.show_progress:
        args.append("--no-progress")
    _run(entry, args, "solve-reform", log_path=os.path.join(reform_dir, "solve.log"))
    sol_npz = os.path.join(reform_dir, "reform_solution.npz")
    if not os.path.exists(sol_npz):
        raise RuntimeError(f"og_runner solve-reform produced no reform_solution.npz in {reform_dir}")
    return serde.load_solution(sol_npz)
