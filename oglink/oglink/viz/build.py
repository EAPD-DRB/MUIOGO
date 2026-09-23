"""Regenerate every figure for an existing across-steps run from the pickles already on disk
-- no model solve. Use to iterate on figure STYLE without re-running OG-Core.

This is the general viz DRIVER: point it at any solved across-steps run, for any country model,
and it rebuilds the full figure set. Nothing about the scenario is hardcoded -- the country model
is PASSED IN (--country), the headline reform is AUTO-DETECTED (the last/most-layered step in the
run, override with --headline-step), and the per-run caveat caption comes from --note. Resolution
order for every input is CLI flag > env var > default:

    --country / OGLINK_COUNTRY   which CountryConfig to visualize (default: phl). Any CountryConfig
                                  defined in oglink.country is selectable by its attribute
                                  name, .name, or .un_code (e.g. phl / philippines / 608).
    --run-dir / OGLINK_RUN_DIR   input  (read-only): the solved across-steps tree
    --fig-dir / OGLINK_FIG_DIR   output: where figures are written (default: <run-dir>/figures,
                                  i.e. INTO the run/scenario directory; override for viz iteration)
    --gbd-csv / OGLINK_GBD_CSV   input  (read-only): IHME GBD burden CSV for health profiles
    --headline-step / OGLINK_HEADLINE_STEP   reform that gets transition/welfare/dashboard/OG-suite
                                  figures (default: the last step in layered_results.json)
    --note    / OGLINK_NOTE      honest caveat caption stamped on every figure

Defaults: figures are written into the run's own figures/ subdir and the GBD CSV is found next to the
run. There is NO built-in run path -- name the run to visualize (--run-dir / $OGLINK_RUN_DIR, or
--coupled-run). The default --note describes THIS experiment's assumptions; pass --note for a different
scenario. A MUIOGO-OG run saves results in a scenario directory; point --run-dir at it and the visuals
land alongside the results, organized under figures/. Runs under the OG model's interpreter (it reads
OG-Core pickles, so it needs ogcore) -- use the env_python from `oglink models list`:

    PYTHONPATH=. <og-model-venv-python> -m oglink.viz --run-dir <solved-run>
"""
from __future__ import annotations

import argparse
import glob
import json
import os

from oglink import country as _country_mod
from oglink import (
    report as og_report,  # MODEL report (report.layered_entry); `report` above is viz's HTML/index module
)
from oglink.viz import plots, report, tables


def safe_read_pickle(path):
    """Read an OG-Core output pickle. Lazy ogcore import: building a deck off OG's native pkl outputs
    runs under the OG model's interpreter (where ogcore lives); the link env imports viz without it."""
    from ogcore.utils import safe_read_pickle as _srp
    return _srp(path)

DEFAULT_COUNTRY = "phl"
# Generic illustrative caveat for the ACROSS-STEPS demo path (build_figures) when it is flagged
# illustrative -- deliberately magnitude-free (no hardcoded "+20%/$50"): the deck shows a run's actual
# results, never baked-in assumptions. A coupled-run deck is REAL (see build_deck_from_coupled_run,
# which defaults illustrative=False), so it carries no caveat at all. Override with --note.
DEFAULT_NOTE = ("Illustrative decomposition -- treat the step magnitudes as indicative; each channel's "
                "calibrated inputs are its own.")
# The full caveat above is shown on the cover. Individual charts carry only this one-line credit caveat.
FIG_CAVEAT = "Illustrative -- magnitudes are indicative."

# index.html / cover organization: a reading order of headline -> how the scenario is built ->
# detailed results. Each section maps to the figure basenames it groups (cover + per-step incidence
# are added automatically by report.write_index). Only files that exist are shown, so a partial
# run degrades gracefully.
_INDEX_SECTIONS = [
    ("Headline",
     ["headline_dashboard", "macro_table", "summary_table", "waterfall_gdp", "waterfall_poorest"]),
    ("How the scenario is built",
     ["channel_inputs", "clews_signal_vs_applied", "capex_by_technology", "emissions_path"]),
    ("Macro & fiscal detail",
     ["macro_transition", "fiscal_transition", "revenue_transition", "rates_transition",
      "public_investment"]),
    ("Health channel",
     ["health_age_profiles", "health_mortality_by_age", "health_morbidity_by_age",
      "health_gdp_split"]),
    ("Welfare -- who wins and loses",
     ["welfare_cev_by_group", "welfare_cev_decomposition", "welfare_cev_by_age"]),
    ("Distribution & composition",
     ["consumption_by_age", "asset_by_age", "income_composition_by_age", "consumption_by_good",
      "consumption_by_good_by_group", "sectoral_reallocation", "energy_by_income"]),
]
# Cover contents list mirrors the index section order (single source of truth).
_DECK_SECTIONS = [title for title, _ in _INDEX_SECTIONS]


def _resolve(cli_val, env_key, default):
    return cli_val or os.environ.get(env_key) or default


def _resolve_country(selector, config_file=None):
    """Delegate to the canonical registry (country.resolve_country): module-defined instances PLUS
    countries-JSON entries (--countries / $OGLINK_COUNTRIES / ./oglink_countries.json), keyed by
    attr/name/un-code/og-repo -- the SAME resolution `run` uses, so a JSON-onboarded country (and the
    'og-phl'-style selectors) reach the portal build too."""
    return _country_mod.resolve_country(selector, config_file=config_file)


def _default_headline(layered):
    """Headline reform = the most-layered (last) non-baseline step in the run."""
    steps = [r.get("step") for r in layered if r.get("step") and r.get("step") != "baseline"]
    return steps[-1] if steps else None


def _default_gbd_csv(run_dir, country):
    """The GBD burden CSV for the run: search UPWARD from `run_dir` for an IHME-GBD_2023_DATA/ dir
    (a run may sit several levels below the repo root, e.g. a battery/<exp>/<exp> layout), else fall
    back to the country's own configured file. General -- no fixed directory depth is assumed."""
    d = os.path.abspath(run_dir)
    for _ in range(5):
        hits = [h for h in glob.glob(os.path.join(d, "IHME-GBD_2023_DATA", "*.csv"))
                if "citation" not in os.path.basename(h).lower()]
        if hits:
            return min(hits)
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return getattr(country, "gbd_burden_csv", None) or None


def _tpi(d):
    p = os.path.join(d, "TPI", "TPI_vars.pkl") if d else None
    return safe_read_pickle(p) if p and os.path.isfile(p) else None


def _params(d):
    p = os.path.join(d, "model_params.pkl") if d else None
    return safe_read_pickle(p) if p and os.path.isfile(p) else None


def _ss(d):
    p = os.path.join(d, "SS", "SS_vars.pkl") if d else None
    return safe_read_pickle(p) if p and os.path.isfile(p) else None


def _start_year(base_dir, country, default=2026):
    """Calendar start year for the transition x-axis, from the run's model_params."""
    try:
        p = safe_read_pickle(os.path.join(base_dir, "model_params.pkl"))
        return int(getattr(p, "start_year", default))
    except Exception:  # noqa: BLE001
        return int(getattr(country.scenario, "og_start_year", default) or default)


def _try(fn, *a, **k):
    """Run a figure builder, never let one failure abort the regen sweep."""
    try:
        return fn(*a, **k)
    except Exception as e:  # noqa: BLE001
        print(f"  [skip] {getattr(fn, '__name__', fn)}: {type(e).__name__}: {e}")
        return None


def _slug(label):
    return label.strip().lstrip("+ ").replace(" ", "_") or "step"


def _run_concordance(base_dir):
    """The PER-RUN energy-port concordance the OG runner discovered + exported next to the baseline
    (`<base_dir>/baseline_meta.json`). Returns a contract.Concordance, or None when the run predates
    the export or solved at a single industry -- callers then degrade to no energy marker."""
    from oglink.contract import Concordance
    meta_path = os.path.join(base_dir, "baseline_meta.json") if base_dir else None
    if not meta_path or not os.path.isfile(meta_path):
        return None
    try:
        with open(meta_path, encoding="utf-8") as f:
            con = json.load(f).get("concordance")
        return Concordance(**con) if con else None
    except (OSError, ValueError, TypeError):
        return None


def _names_from_meta(base_dir):
    """The (industry_names, good_names) the OG runner recorded next to the baseline
    (`baseline_meta.json`, from the model's PROD_DICT/CONS_DICT) so figures label sectors/goods by name
    instead of "sector k". (None, None) when unrecorded (an older run, single-industry, or a name/M
    mismatch) -- the label helpers then fall back to numbered labels, so any model still renders."""
    meta_path = os.path.join(base_dir, "baseline_meta.json") if base_dir else None
    if not meta_path or not os.path.isfile(meta_path):
        return None, None
    try:
        with open(meta_path, encoding="utf-8") as f:
            m = json.load(f)
        return m.get("industry_names"), m.get("good_names")
    except (OSError, ValueError):
        return None, None


def _render_deck(country, dir_of, layered, fig_dir, index_path, *, headline_step=None,
                 gbd_csv=None, note=DEFAULT_NOTE, illustrative=True, og_appendix=False):
    """Render the full figure deck + index, resolving each role (``"baseline"`` and the step
    labels) to a solved-pickle directory through the ``dir_of(label) -> dir`` callable. This is
    the layout-agnostic core: the across-steps driver and the coupled-run bridge differ only in
    how they map labels to directories, so any country/model that produces a (baseline, reform)
    pair can be visualized -- nothing about the on-disk layout is assumed here.

    `illustrative` (default True) is the single switch for the placeholder phase: while True the
    charts carry the short caveat and the unit-labelled "model units" disclosures; flip it to False
    once the run is calibrated and every figure drops that language with no per-figure edits."""
    os.makedirs(fig_dir, exist_ok=True)
    # Clean regen: a rerun of THIS simulation should leave exactly this run's figures (no stale files
    # from a prior run that produced a channel this one skipped). index.html/results.csv (in out_dir)
    # are overwritten in place; here we clear the figures dir before repopulating it.
    import shutil as _shutil
    for _stale in glob.glob(os.path.join(fig_dir, "*.png")):
        try:
            os.remove(_stale)
        except OSError:
            pass
    _shutil.rmtree(os.path.join(fig_dir, "per_step"), ignore_errors=True)
    industry_names, good_names = _names_from_meta(dir_of("baseline"))   # label sectors/goods by name
    # The cover shows whatever caption the caller passed (`note`), independent of `illustrative` -- so a
    # real run can still carry a --note and a results-only run (note="") carries none. The per-figure
    # FIG_CAVEAT is shown ONLY in the illustrative phase (a real run stamps no "illustrative" credit).
    full_note = note or ""
    note = FIG_CAVEAT if illustrative else ""
    base_dir = dir_of("baseline")
    conc = _run_concordance(base_dir)             # per-run energy ports (None / unset -> no energy marker)
    ie = conc.energy_good_index if conc is not None else None
    if headline_step is None:
        headline_step = _default_headline(layered)
    print(f"       country {country.name}   headline {headline_step!r}")
    print(f"       gbd  {gbd_csv if gbd_csv and os.path.isfile(gbd_csv) else '(none -- health profiles skipped)'}")

    # --- top-level figures (across steps) ---------------------------------------
    _multi = len([r for r in layered if "macro" in r]) >= 2   # layered views need >=2 scenarios
    _try(plots.across_steps_waterfall, layered, fig_dir, note=note)
    _try(plots.energy_physical, country, fig_dir, illustrative=illustrative)
    if _multi:  # the step-decomposition CSV is redundant for a single coupled run (see results.csv)
        _try(tables.across_steps_table, layered, os.path.join(fig_dir, "across_steps_summary.csv"))
    # index.html (written at the end) is the SINGLE entry point -- no separate CDN-dependent report.html.

    # --- OG-Core's own canonical ~31-plot suite: OPT-IN appendix (default off -> lean deck) --------
    headline_dir = dir_of(headline_step)
    if og_appendix and headline_dir and os.path.isdir(headline_dir):
        _try(plots.og_default_outputs, base_dir, headline_dir,
             os.path.join(fig_dir, "og_suite"), plots=True)
        print(f"  (OG-Core standard suite -> {os.path.join(fig_dir, 'og_suite')}/  [opt-in appendix])")

    base_tpi = _tpi(base_dir)
    base_ss = _ss(base_dir)  # also feeds the CEV/distribution/composition figures below
    factor = float(base_ss["factor"]) if base_ss and "factor" in base_ss else None
    start_year = _start_year(base_dir, country)

    # --- editorial transition-path figures for the headline reform --------------
    base_params = _params(base_dir)                   # also feeds closure marker, energy, health, welfare
    headline_params = _params(headline_dir)
    headline_tpi = _tpi(headline_dir)
    if base_tpi is not None and headline_tpi is not None:
        for fn in (plots.macro_transition, plots.fiscal_transition,
                   plots.revenue_transition, plots.rates_transition,
                   plots.public_investment):
            _try(fn, base_tpi, headline_tpi, fig_dir, start_year=start_year, note=note,
                 params=base_params)

    # --- energy-system linkage (the CLEWS-to-OG inputs) -------------------------
    # The energy-price channel's applied wedge = the FIRST reform step's params (the +20% energy-price
    # proxy), so the flagship compares the CLEWS energy-price ratio to the wedge that channel actually
    # applied -- not the headline's cumulative energy+carbon wedge.
    ep_params = _params(dir_of(layered[0]["step"])) if layered else None
    ep_ref = ep_params if ep_params is not None else headline_params
    energy_linkage = []  # these read the CLEWS scenario/cost files; capture so a skip is never silent
    if base_params is not None and ep_ref is not None:
        energy_linkage.append(_try(plots.clews_signal_vs_applied, country, base_params, ep_ref, fig_dir,
                                   note=note, concordance=conc, illustrative=illustrative))
    energy_linkage.append(_try(plots.capex_by_technology, country, fig_dir, note=note,
                               illustrative=illustrative))
    if base_tpi is not None:
        energy_linkage.append(_try(plots.channel_inputs_over_time, country, base_tpi, fig_dir, note=note,
                                   illustrative=illustrative))
    if not any(energy_linkage):  # never silent (design guide): say why the "how it's built" figures are absent
        print("  (energy-linkage figures skipped: this run's CLEWS scenario/cost files were not found)")

    # --- health-channel visuals -------------------------------------------------
    if gbd_csv and os.path.isfile(gbd_csv):
        _try(plots.gbd_age_profiles, gbd_csv, country.name, int(country.gbd_year), fig_dir, note=note)
    if base_params is not None and headline_params is not None:
        _try(plots.mortality_by_age, base_params, headline_params, fig_dir, note=note)
        _try(plots.morbidity_by_age, base_params, headline_params, fig_dir, note=note)
        # No population-share-by-age chart: reform omega (disease_pop, infer_pop=True, single seed) and
        # baseline omega (baseline_pop, infer_pop=False, observed UN pop) come from DIFFERENT get_pop_objs
        # windows, so their difference is ~99.9% construction artifact (single-age heaping + a window
        # kink), not the health signal. The real mortality effect on the age structure is smooth and
        # ~3e-4 pp -- negligible; the health story is carried by lives-saved + mortality_by_age above.
    _try(plots.gdp_split, layered, fig_dir, note=note, illustrative=illustrative)

    # --- welfare: consumption-equivalent variation (CEV) ------------------------
    headline_ss = _ss(headline_dir)  # base_ss loaded once above
    if None not in (base_ss, headline_ss, base_params, headline_params):
        _try(plots.cev_by_group, base_ss, headline_ss, base_params, headline_params,
             fig_dir, note=note)
        _try(plots.cev_decomposition, base_ss, headline_ss, base_params, headline_params,
             fig_dir, note=note)
    if base_tpi is not None and headline_tpi is not None and None not in (base_params, headline_params):
        _try(plots.cev_by_age, base_tpi, headline_tpi, base_params, headline_params,
             fig_dir, note=note)

    # --- distributional richness ------------------------------------------------
    _try(plots.energy_demand_by_group, layered, fig_dir, note=note)
    if None not in (base_ss, headline_ss, base_params):
        _try(plots.consumption_by_age, base_ss, headline_ss, base_params, fig_dir, note=note)
        _try(plots.asset_by_age, base_ss, headline_ss, base_params, fig_dir, note=note)
    if base_tpi is not None and headline_tpi is not None and base_params is not None:
        _try(plots.income_composition_by_age, base_tpi, headline_tpi, base_params, fig_dir, note=note)

    # --- multi-good / multi-sector composition (the GE structure) ---------------
    # `conc` (the run's energy good/industry indices) was loaded once at the top from baseline_meta.json
    if None not in (base_ss, headline_ss, base_params):
        _try(plots.consumption_by_good, base_ss, headline_ss, base_params, fig_dir, note=note,
             concordance=conc, good_names=good_names)
        _try(plots.sectoral_reallocation, base_ss, headline_ss, base_params, fig_dir, note=note,
             concordance=conc, industry_names=industry_names)
    if base_tpi is not None and headline_tpi is not None and base_params is not None:
        _try(plots.consumption_by_good_by_group, base_tpi, headline_tpi, base_params, fig_dir, note=note,
             concordance=conc, good_names=good_names)

    # --- one-page headline dashboard --------------------------------------------
    if None not in (base_tpi, headline_tpi, base_ss, headline_ss, base_params, headline_params):
        _try(plots.headline_dashboard, layered, base_tpi, headline_tpi, base_ss, headline_ss,
             base_params, headline_params, country, fig_dir, start_year=start_year, note=note,
             illustrative=illustrative)

    # --- deck front matter & at-a-glance summary --------------------------------
    # The OG-standard macro-aggregates table (output/consumption/investment/capital/labour + rates,
    # year-by-year + window + SS) is the richer summary economists expect; render it whenever a
    # baseline+reform TPI pair is present. The step-decomposition summary_table adds value only with
    # >=2 layered scenarios, so it is skipped for a single coupled run (where it would be one row).
    if base_tpi is not None and headline_tpi is not None:
        _try(tables.macro_table_figure, base_tpi, headline_tpi, start_year, fig_dir, note=note)
        # ONE authoritative CSV of the headline numbers in the deck root -- the source of truth behind
        # the rendered macro_table.png (not an image-only table; copyable, re-analysable, like OG's).
        try:
            og_report.macro_table(base_tpi, headline_tpi, start_year).to_csv(
                os.path.join(os.path.dirname(index_path) or ".", "results.csv"))
        except Exception as e:  # noqa: BLE001 -- the CSV is a convenience; never abort the deck
            print(f"  (results.csv skipped: {type(e).__name__})")
    if _multi:
        _try(tables.summary_table, layered, fig_dir, note=note)
    # The cover carries the FULL caveat + the plain-language scenario description.
    _try(tables.cover_page, layered, country, _DECK_SECTIONS, fig_dir, note=full_note,
         illustrative=illustrative)

    # --- per-step incidence hero ------------------------------------------------
    # the incidence hero keys off the energy good (energy budget share); with no isolated energy good
    # (the country can't be coupled on energy) there is nothing to attribute incidence to, so skip it.
    made = []
    if ie is None:
        print("  (skip per-step incidence: this run has no isolated energy good)")
    for r in layered if ie is not None else []:
        label = r.get("step")
        if "macro" not in r or label == "baseline":
            continue
        reform_tpi = _tpi(dir_of(label))
        if base_tpi is None or reform_tpi is None:
            print(f"  (skip incidence for {label!r}: pickle missing)")
            continue
        sdir = os.path.join(fig_dir, "per_step", _slug(label))
        if _try(plots.incidence_hero, base_tpi, reform_tpi, ie, sdir,
                title=f"{country.name}: {label}", note=note, factor=factor) is not None:
            made.append(label)
    print(f"Regenerated top-level figures in {fig_dir}/ + incidence for: {made}")

    # --- scenario entry point: one index.html at the run-dir root linking the whole deck --------
    index = _try(report.write_index, fig_dir, index_path,
                 _INDEX_SECTIONS, country=country, note=full_note)
    if index:
        print(f"Wrote scenario index -> {index}")


def build_figures(country, run_dir, fig_dir, gbd_csv, *, headline_step=None, note=DEFAULT_NOTE,
                  illustrative=True, og_appendix=False):
    """Rebuild the full figure set from a solved ACROSS-STEPS tree under `run_dir` (``baseline/`` +
    per-step dirs + ``layered_results.json``), writing to `fig_dir`. A thin wrapper over
    `_render_deck` that just resolves the on-disk across-steps layout; `headline_step` None ->
    auto-detect (last layered step). `og_appendix` opt-in adds OG-Core's ~31-plot suite."""
    with open(os.path.join(run_dir, "layered_results.json"), encoding="utf-8") as f:
        layered = json.load(f)
    print(f"regen: read {run_dir}\n       write {fig_dir}")
    _render_deck(country, lambda label: os.path.join(run_dir, label) if label else None,
                 layered, fig_dir, os.path.join(run_dir, "index.html"),
                 headline_step=headline_step, gbd_csv=gbd_csv, note=note, illustrative=illustrative,
                 og_appendix=og_appendix)


def _read_manifest(coupled_dir):
    """The `oglink_manifest.json` a `run coupled` writes (concordance, channels, scenario, model)."""
    p = os.path.join(coupled_dir, "oglink_manifest.json")
    if not os.path.isfile(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _discover_baseline_cache(coupled_dir, manifest):
    """Locate the cached baseline solve for a coupled run -- general, no hardcoded cache tag. The
    runner writes it to ``<run-root>/_og_baseline_cache/<og-pkg>-<ver>-<calib>/``; the run root is
    some ancestor of the experiment dir, so walk up looking for it, and, when several caches exist,
    keep those whose `baseline_meta.json` concordance matches the run's manifest, newest first."""
    cands, d = [], coupled_dir
    for _ in range(4):                       # the cache lives at the run root, an ancestor of this dir
        cands += glob.glob(os.path.join(d, "_og_baseline_cache", "*"))
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    cands = [c for c in cands if os.path.isfile(os.path.join(c, "model_params.pkl"))
             and os.path.isfile(os.path.join(c, "SS", "SS_vars.pkl"))]
    if len(cands) <= 1:
        return cands[0] if cands else None
    want = manifest.get("concordance")

    def _meta_conc(c):
        try:
            with open(os.path.join(c, "baseline_meta.json"), encoding="utf-8") as f:
                return json.load(f).get("concordance")
        except (OSError, ValueError):
            return None
    matched = [c for c in cands if want and _meta_conc(c) == want] or cands
    return max(matched, key=os.path.getmtime)


def build_deck_from_coupled_run(coupled_dir, country, *, out_dir=None, clews_base=None,
                                clews_reform=None, fig_dir=None, gbd_csv=None,
                                step_label=None, note=None, illustrative=False, og_appendix=False):
    """Build the full rich deck from ONE solved `run coupled` output dir, with NO new solve.

    ``illustrative`` defaults to False: a coupled run IS the real integrated result (the electricity
    price is the actual CLEWS signal, not a +20% stand-in), so the deck shows results with no baked
    "illustrative" caveat and no hardcoded magnitudes -- the cover and titles carry only the run's own
    country/scenario. Pass ``illustrative=True`` (or ``--note``) for a controlled-magnitude experiment.

    `out_dir` collects the whole simulation deck in ONE directory -- `out_dir/figures/` + `out_dir/
    index.html` -- mirroring OG-Core's single save-dir convention, so a simulation's results are one
    self-contained, discoverable folder. Default (`out_dir=None`) writes beside the run itself.

    General over country/model: the baseline is the run's own cached solve and the single reform is
    the coupled reform already on disk; the energy concordance and applied channels are READ from the
    run's manifest + baseline_meta.json. Nothing country- or path-specific is hardcoded. Figures that
    need a baseline+reform pair (macro/fiscal/welfare/health/distribution/composition) are the genuine
    current-calibration deck; the across-steps multi-bar waterfall is intentionally omitted for a single
    step (the OG-style macro-aggregates table is the summary instead). `clews_base`/`clews_reform` (or
    the run's manifest scenario) point the emissions + energy-linkage figures at the CLEWS output."""
    coupled_dir = os.path.abspath(coupled_dir)
    manifest = _read_manifest(coupled_dir)
    # The run records the country it was solved for; --country is an override -> warn on a mismatch
    # so a wrong --country can't silently render one country's labels over another's pickles.
    m_country = manifest.get("un_code") or manifest.get("country")
    if m_country and str(m_country) not in (str(country.un_code), country.name):
        print(f"  [warn] --country {country.name}/{country.un_code} != the run's manifest "
              f"({m_country}); rendering with the passed-in country")
    # CLEWS scenario dirs drive the emissions + energy-linkage figures. Prefer explicit args, else the
    # dirs the run recorded in its manifest; set them on country.scenario so those figures can find the
    # CLEWS output (they are otherwise blank on the CountryConfig, which the coupling run fills at solve
    # time). Guarded: a frozen scenario just leaves those figures to skip (logged later, never silent).
    sc = manifest.get("scenario") or {}
    # CLEWS source for the emissions + energy-linkage figures, in priority order:
    #   1. explicit --clews-base/--clews-reform;
    #   2. clews_source/{base,reform} CO-LOCATED with the run (staged by `run` so the deck is
    #      self-contained -- rebuildable even after the MUIOGO case moves/changes);
    #   3. the external scenario dirs the manifest recorded (the fallback -- what the run read live).
    _local = os.path.join(coupled_dir, "clews_source")
    _lbase, _lreform = os.path.join(_local, "base"), os.path.join(_local, "reform")
    base_src = clews_base or (_lbase if os.path.isdir(_lbase) else sc.get("base_dir"))
    reform_src = clews_reform or (_lreform if os.path.isdir(_lreform) else sc.get("reform_dir"))
    for _attr, _val in (("base_dir", base_src), ("reform_dir", reform_src)):
        if _val and getattr(country, "scenario", None) is not None:
            try:
                setattr(country.scenario, _attr, _val)
            except Exception:  # noqa: BLE001 -- immutable scenario: energy/emissions figures skip loudly
                pass
    reform_dir = os.path.join(coupled_dir, "reform")
    # Prefer a baseline dir the manifest records (forward-compatible: once the runner writes it, no
    # discovery needed); else fall back to locating the cache under the run root.
    _mb = manifest.get("baseline_dir")
    base_dir = _mb if (_mb and os.path.isdir(_mb)) else _discover_baseline_cache(coupled_dir, manifest)
    if not os.path.isdir(reform_dir):
        raise SystemExit(f"no reform/ under {coupled_dir}")
    if base_dir is None:
        raise SystemExit(f"no cached baseline solve found for {coupled_dir} "
                         "(looked under <run-root>/_og_baseline_cache/*)")
    base_tpi, reform_tpi = _tpi(base_dir), _tpi(reform_dir)
    if base_tpi is None or reform_tpi is None:
        raise SystemExit("baseline or reform TPI pickle missing -- cannot build the deck")
    # Energy good: the baseline's exported concordance (baseline_meta.json) is the single source --
    # _render_deck re-derives the SAME value for the marker/incidence, so the layered row's energy
    # rows and the deck's energy figures stay consistent (no separate manifest fallback to diverge).
    conc = _run_concordance(base_dir)
    ie = conc.energy_good_index if conc is not None else None
    channels = [c.get("id") for c in manifest.get("channels", [])]
    label = step_label or (manifest.get("experiment") or {}).get("name") or "reform"
    if label == "baseline":                  # reserved role name -> keep the reform step distinct
        label = "reform"
    layered = [og_report.layered_entry(label, base_tpi, reform_tpi,
                                       energy_good_index=ie, channels=channels)]

    def dir_of(which):
        return base_dir if which == "baseline" else (reform_dir if which == label else None)

    out_dir = os.path.abspath(out_dir) if out_dir else coupled_dir  # one dir for the whole sim deck
    fig_dir = fig_dir or os.path.join(out_dir, "figures")
    # explicit arg > a path the manifest records > search upward from the run for the burden CSV
    gbd_csv = gbd_csv or manifest.get("gbd_csv") or _default_gbd_csv(coupled_dir, country)
    note = note or ""      # results-only by default: no editorial caption unless --note is given
    print(f"coupled-deck: read {coupled_dir}\n       baseline {base_dir}\n       write {out_dir}")
    _render_deck(country, dir_of, layered, fig_dir, os.path.join(out_dir, "index.html"),
                 headline_step=label, gbd_csv=gbd_csv, note=note, illustrative=illustrative,
                 og_appendix=og_appendix)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--country", help="country model to visualize (default: phl)")
    ap.add_argument("--countries", default=None,
                    help="countries JSON defining your own CountryConfig entries (default: "
                         "$OGLINK_COUNTRIES, else ./oglink_countries.json if present) -- the same "
                         "file `run --countries` reads")
    src = ap.add_mutually_exclusive_group()   # one input layout or the other, not both
    src.add_argument("--run-dir", help="input solved across-steps tree (read-only)")
    src.add_argument("--coupled-run", help="build the deck from a single solved `run coupled` output "
                                           "dir (uses its cached baseline + reform; no new solve)")
    ap.add_argument("--out-dir", help="collect the whole coupled-run deck in ONE directory "
                                      "(out-dir/figures/ + out-dir/index.html); with --coupled-run only")
    ap.add_argument("--clews-base", help="CLEWS baseline scenario dir (its AnnualTechnologyEmission + "
                                         "cost-of-electricity files feed the emissions + energy-linkage "
                                         "figures); default: the run's manifest scenario")
    ap.add_argument("--clews-reform", help="CLEWS reform scenario dir (see --clews-base)")
    ap.add_argument("--fig-dir", help="output dir for figures (viz-local)")
    ap.add_argument("--gbd-csv", help="IHME GBD burden CSV for health age-profile figures")
    ap.add_argument("--headline-step", help="reform step for transition/welfare/dashboard figures "
                                            "(default: last step in layered_results.json)")
    ap.add_argument("--note", help="honest caveat caption stamped on every figure")
    ap.add_argument("--calibrated", action="store_true",
                    help="[across-steps] drop the illustrative/model-units caveats (results are real)")
    ap.add_argument("--illustrative", action="store_true",
                    help="[coupled-run] mark a controlled-magnitude experiment so its deck carries the "
                         "illustrative caveat -- default: a coupled run is real (results-only, no caveat)")
    ap.add_argument("--og-appendix", action="store_true",
                    help="also render OG-Core's ~31-plot standard suite into figures/og_suite/ "
                         "(off by default -> a lean deck of only the curated coupling figures)")
    args = ap.parse_args(argv)

    country = _resolve_country(_resolve(args.country, "OGLINK_COUNTRY", DEFAULT_COUNTRY),
                               config_file=args.countries)
    illustrative = not args.calibrated

    # A single coupled run (the live `run coupled` output): build the deck off its cached baseline +
    # reform, no new solve. fig-dir/gbd-csv None -> the function defaults them under the coupled dir.
    # A coupled run is REAL -> illustrative defaults False (results-only, no caveat); --illustrative marks
    # a controlled-magnitude experiment. note None -> no caption unless --note is given.
    coupled = _resolve(args.coupled_run, "OGLINK_COUPLED_RUN", None)
    if coupled:
        build_deck_from_coupled_run(
            coupled, country,
            out_dir=_resolve(args.out_dir, "OGLINK_OUT_DIR", None),
            clews_base=_resolve(args.clews_base, "OGLINK_CLEWS_BASE", None),
            clews_reform=_resolve(args.clews_reform, "OGLINK_CLEWS_REFORM", None),
            fig_dir=_resolve(args.fig_dir, "OGLINK_FIG_DIR", None),
            gbd_csv=_resolve(args.gbd_csv, "OGLINK_GBD_CSV", None),
            note=_resolve(args.note, "OGLINK_NOTE", None),
            illustrative=args.illustrative, og_appendix=args.og_appendix)
        return

    run_dir = _resolve(args.run_dir, "OGLINK_RUN_DIR", None)
    if not run_dir:                       # no machine-specific default -- the run to visualize must be named
        raise SystemExit("no run to visualize: pass --run-dir <solved across-steps tree> (or "
                         "$OGLINK_RUN_DIR), or --coupled-run <run coupled output dir>.")
    # Default: write figures INTO the run/scenario directory (organized under figures/), so a
    # MUIOGO-OG run's results and its visuals live together. Override --fig-dir for viz iteration.
    fig_dir = _resolve(args.fig_dir, "OGLINK_FIG_DIR", os.path.join(run_dir, "figures"))
    gbd_csv = _resolve(args.gbd_csv, "OGLINK_GBD_CSV", _default_gbd_csv(run_dir, country))
    note = _resolve(args.note, "OGLINK_NOTE", DEFAULT_NOTE)
    headline_step = _resolve(args.headline_step, "OGLINK_HEADLINE_STEP", None)  # None -> auto-detect

    build_figures(country, run_dir, fig_dir, gbd_csv, headline_step=headline_step, note=note,
                  illustrative=illustrative, og_appendix=args.og_appendix)


if __name__ == "__main__":
    main()
