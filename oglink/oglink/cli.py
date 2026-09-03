"""Command-line runner: the management surface for the channel framework.

  python -m oglink list                 # named experiments
  python -m oglink channels             # the channel functions + direction
  python -m oglink run clean_incidence  # build baseline, apply channels, solve, report
  python -m oglink run coupled --out ./runs
"""
from __future__ import annotations

import argparse

from . import clews_io, experiments
from .report import print_report


def main(argv=None):
    ap = argparse.ArgumentParser(prog="oglink")
    sub = ap.add_subparsers(dest="cmd")

    rp = sub.add_parser("run", help="run a named experiment")
    rp.add_argument("experiment")
    rp.add_argument("--country", default=None,
                    help="country to run (name / UN code / og-repo key, e.g. 'phl' or 'og-zaf'); "
                         "default: $OGLINK_COUNTRY, else the packaged PHL example")
    rp.add_argument("--countries", default=None,
                    help="countries JSON defining your own CountryConfig entries (default: "
                         "$OGLINK_COUNTRIES, else ./oglink_countries.json if present; see "
                         "oglink_countries.example.json)")
    rp.add_argument("--workers", type=int, default=7, help="OG-Core J-loop worker processes (use multiprocess; avoid 1)")
    rp.add_argument("--out", default="./oglink_runs")
    rp.add_argument("--no-progress", action="store_true")
    rp.add_argument("--rebuild-baseline", action="store_true",
                    help="force a fresh baseline solve, ignoring any cached one (e.g. to pick up newer "
                         "UN demographics or a re-baked calibration)")
    rp.add_argument("--clews-base", default=None,
                    help="CLEWS baseline scenario dir (overrides $OGLINK_CLEWS_BASE / the MUIOGO-install "
                         "resolution); e.g. <MUIOGO>/WebAPP/DataStorage/<case>/res/<run>/csv")
    rp.add_argument("--clews-reform", default=None, help="CLEWS reform scenario dir (the reform side)")
    rp.add_argument("--clews-run", default=None,
                    help="CLEWS/MUIOGO run dir recorded in the manifest for provenance")

    sub.add_parser("list", help="list named experiments")
    sub.add_parser("channels", help="list registered channels")

    mp = sub.add_parser("models", help="manage the installed OG-model register")
    msub = mp.add_subparsers(dest="models_cmd")
    mr = msub.add_parser("register", help="record an installed OG model by its checkout dir")
    mr.add_argument("--path", required=True, help="the OG model's checkout dir (must contain .venv/)")
    mr.add_argument("--python", default=None,
                    help="explicit interpreter for a non-uv env (conda/system); bypasses the "
                         ".venv/{bin,Scripts} probe. Pair with --source-dir if it lives outside <path>/.venv")
    mr.add_argument("--source-dir", default=None,
                    help="the package source dir, if not <path>/<package> (needed when --python points "
                         "outside <path>/.venv, since the source can't be derived from the interpreter)")
    mr.add_argument("--key", default=None, help="repo key (default: the dir name, e.g. OG-PHL -> og-phl)")
    mr.add_argument("--calibration", default=None,
                    help="multisector param file to use (default: auto-pick the lone couplable one, "
                         "else single-industry)")
    mr.add_argument("--no-discovery", action="store_true",
                    help="skip calibration discovery (record single-industry unless --calibration given)")
    mr.add_argument("--registry", default=None, help="register file to write (default: $OGLINK_MODEL_REGISTRY or ./og_model_registry.json)")
    mc = msub.add_parser("calibrations", help="show a registered model's calibration choices (no solve)")
    mc.add_argument("model", help="repo key / package / country (e.g. og-phl)")
    mc.add_argument("--refresh", action="store_true",
                    help="re-read the package source (cheap) and update the saved status")
    mc.add_argument("--registry", default=None)
    ml = msub.add_parser("list", help="list registered OG models")
    ml.add_argument("--registry", default=None)

    args = ap.parse_args(argv)

    if args.cmd == "list":
        import inspect
        for n in experiments.names():
            doc = (inspect.getdoc(experiments.get(n)) or "").splitlines()
            print(f"{n:16} {doc[0] if doc else ''}")
        return
    if args.cmd == "channels":
        import inspect

        from . import channels
        for name in (n for n in dir(channels) if not n.startswith("_")):
            fn = getattr(channels, name)
            if not (callable(fn) and getattr(fn, "__module__", "") == channels.__name__):
                continue
            direction = "og->clews" if name.startswith("emit_") else "clews->og / policy"
            doc = (inspect.getdoc(fn) or "").splitlines()
            print(f"{name:20} {direction:18} {doc[0] if doc else ''}")
        return
    if args.cmd == "models":
        from . import discovery, models
        if args.models_cmd == "register":
            rec = models.register(args.path, key=args.key, registry_file=args.registry,
                                  calibration=args.calibration, run_discovery=not args.no_discovery,
                                  python=args.python, source_dir=args.source_dir)
            print(f"registered {rec['key']} ({rec['package']} {rec['version'] or '?'}) -> {rec['env_python']}")
            cal = rec.get("calibration")
            print(f"  calibration: {cal if cal else '(single-industry -- energy channels skip)'}")
            if rec.get("findings"):
                discovery.print_calibrations(rec["findings"], print)
            print(f"  written to {rec['registry']}")
        elif args.models_cmd == "calibrations":
            findings = models.calibrations(args.model, args.registry, refresh=args.refresh)
            if findings is None:
                print(f"no calibration status for {args.model} (not discovered and no source on disk)")
            else:
                if findings.get("discovered_at") and not args.refresh:
                    print(f"  (saved status from {findings['discovered_at']}; --refresh to re-read)")
                discovery.print_calibrations(findings, print)
        elif args.models_cmd == "list":
            rows = models.list_models(args.registry)
            if not rows:
                print("no OG models registered (run: oglink models register --path <dir>)")
            for key, pkg, ver, cal, cc, ok in rows:
                coup = "" if cc is None else f" couplable={cc}"
                print(f"  [{'x' if ok else ' '}] {key:10} {pkg:12} {ver or '?':8} "
                      f"calib={cal or 'single-industry'}{coup}" + ("" if ok else "  (interpreter missing)"))
        else:
            mp.print_help()
        return
    if args.cmd == "run":
        import os
        from functools import partial

        from . import framework, registry, runtime
        from .country import CLEWS_SCENARIO_HELP, resolve_country
        from .manifest import write_run_manifest
        from .muiogo_run import preflight

        exp = experiments.get(args.experiment)
        # Country: CLI flag > $OGLINK_COUNTRY > the packaged PHL example. Countries beyond the packaged
        # ones are defined declaratively in a countries JSON (--countries / $OGLINK_COUNTRIES /
        # ./oglink_countries.json) -- onboarding never edits link source.
        country = resolve_country(args.country or os.environ.get("OGLINK_COUNTRY") or "phl",
                                  config_file=args.countries)
        print(f"Country: {country.name} (un {country.un_code}, OG model {country.og_repo})")
        cfg = runtime.RunnerConfig(num_workers=args.workers, show_progress=not args.no_progress,
                                   rebuild=args.rebuild_baseline)
        # CLEWS scenario source: CLI flag > env / MUIOGO-install resolution (country.clews_scenario_dir)
        if args.clews_base:
            country.scenario.base_dir = args.clews_base
        if args.clews_reform:
            country.scenario.reform_dir = args.clews_reform
        pre = {}
        for side, d in (("base", country.scenario.base_dir), ("reform", country.scenario.reform_dir)):
            status = "ok" if d and os.path.isdir(d) else "NOT FOUND -- CLEWS-reading channels will fail"
            print(f"CLEWS {side:6} scenario: {d or '(unset)'}  [{status}]")
            if not (d and os.path.isdir(d)):
                print(f"  {CLEWS_SCENARIO_HELP}")
            else:
                pre[side] = preflight(d, label=side)   # loud export checklist BEFORE the expensive solve
        # Health-data notice BEFORE the solve: the GBD extract is machine-local (never shipped with the
        # repo), so a fresh install runs without it and the health channel skips. Say so now -- a tester
        # should not learn it 20 minutes into the solve.
        if getattr(country, "gbd_burden_csv", None) is None:
            print("health data: no GBD export on disk -> the health channel will SKIP this run "
                  "(everything else proceeds). To enable it, place the GBD ambient-PM2.5 burden CSV "
                  "under IHME-GBD_2023_DATA/.")
        entry = registry.lookup(country)    # OG-model provenance for the manifest (and fail-fast)
        # FAIL-FAST, not warn-then-burn: an experiment that unconditionally sources the energy price
        # (its source calls _auto_price_ratio) needs a LEVELIZED 'auto' source in BOTH scenario dirs --
        # the cost-of-electricity workbook, OR the LCOE inputs (a busbar code + the production/use/cost
        # CSVs). The EBb4 marginal does NOT satisfy 'auto' (it is opt-in only). If no levelized source
        # exists -- and the registered calibration is couplable, so the energy legs won't just skip --
        # the run is GUARANTEED to die after the multi-minute baseline solve; refuse now with the fix
        # instead. (calibration None -> single-industry -> energy legs skip -> no gate.)
        import inspect

        from . import lcoe as _lcoe
        from . import signals as _signals
        try:
            needs_price = "_auto_price_ratio" in inspect.getsource(exp)
        except (OSError, TypeError):        # no source (frozen/builtin) -> can't tell -> don't gate
            needs_price = False
        if needs_price and entry.calibration and len(pre) == 2:
            dirs = (country.scenario.base_dir, country.scenario.reform_dir)
            workbook = all(_signals._has_cost_xlsx(d) for d in dirs)
            busbar = getattr(country, "busbar_electricity", None)
            # LCOE needs the input CSVs AND a busbar code that names a real produced commodity -- a
            # present-but-wrong busbar would otherwise fail only AFTER the multi-minute baseline solve.
            lcoe_ok = bool(busbar) and all(_signals._has_lcoe_inputs(d) for d in dirs) and \
                all(_lcoe.has_busbar_producers(d, busbar) for d in dirs)
            if not (workbook or lcoe_ok):
                raise SystemExit(
                    f"experiment {args.experiment!r} needs an energy-price source, but 'auto' has neither "
                    "a cost-of-electricity workbook nor the LCOE inputs (CountryConfig.busbar_electricity "
                    "+ the ProductionByTechnologyByMode / UseByTechnologyByMode / annual cost CSVs) in "
                    "both scenario dirs (see the export checklist above). A MUIOGO CBC solve produces the "
                    "LCOE CSVs; set busbar_electricity for the country. (The EBb4 marginal is NOT an 'auto' "
                    "source -- it is a degenerate short-run price, opt-in via kind='marginal' only.)")
        og_model = {"repo": entry.key, "package": entry.package, "version": entry.version,
                    "env_python": entry.env_python}
        ctx = framework.run(
            exp, country,
            export_baseline=partial(runtime.export_baseline, cfg=cfg),
            solve_reform=partial(runtime.solve_reform, cfg=cfg),
            out_root=args.out)
        print_report(ctx)
        if ctx.base_tpi is not None and ctx.reform_tpi is not None:
            import os

            from .report import macro_table
            mt_path = os.path.join(args.out, args.experiment, "macro_table.csv")
            try:
                os.makedirs(os.path.dirname(mt_path), exist_ok=True)
                macro_table(ctx.base_tpi, ctx.reform_tpi, country.scenario.og_start_year).to_csv(mt_path)
                print("Wrote macro table:", mt_path)
            except Exception as e:  # noqa: BLE001 -- the CSV is a convenience; never fail the run for it
                print(f"(macro table CSV skipped: {type(e).__name__})")
        if ctx.clews_inputs:
            written = clews_io.write_all(ctx, os.path.join(args.out, args.experiment, "clews_inputs"))
            print("Wrote CLEWS inputs:", written)
        baseline_dir = runtime._cache_dir(args.out, entry, country, cfg)  # OG baseline cache this run used
        manifest = write_run_manifest(os.path.join(args.out, args.experiment), exp, country, ctx,
                                      clews_run=args.clews_run, og_model=og_model,
                                      baseline_dir=baseline_dir, gbd_csv=country.gbd_burden_csv)
        print("Wrote run manifest:", manifest)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
