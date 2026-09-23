"""All figures for the coupled OG-Core x CLEWS deck -- one module, organized by section
(core/waterfall, macro & fiscal transition, energy-system linkage, health, welfare, distribution
& composition, and the one-page dashboard). The driver in build.py orchestrates these; the shared
house theme and plotting primitives live in style.py. Import-safe (matplotlib Agg)."""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import numpy as np
from scipy.optimize import brentq

from oglink import health_profile, signals
from oglink.signals import _cost_xlsx

from . import style

style.apply()
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# ============================== FIGURES ==============================

LOSS, GAIN = style.LOSS, style.GAIN


def _labels(J, lambdas=None):
    return style.income_labels(J, lambdas)


def _bridge(values):
    """Waterfall bridge math: from a sequence of cumulative `values`, the per-step MARGINAL
    contributions (`marg`) and the running cumulative with a leading zero (`cum`, length n+1).
    The one place this lives, shared by _waterfall and the dashboard's _panel_waterfall."""
    marg = np.diff(np.concatenate([[0.0], values]))
    cum = np.concatenate([[0.0], np.cumsum(marg)])
    return marg, cum


def incidence_hero(base_tpi, reform_tpi, i_energy, out_dir, *, title, note, factor=None,
                   name="incidence", kicker="distributional incidence"):
    """Three linked panels: (1) the incidence curve -- welfare % change by income group as a
    dot-and-line, diverging color by sign; (2) the MECHANISM -- welfare vs baseline energy
    budget share; (3) the DOLLAR effect per household (approximate, via the OG income factor)."""
    from oglink import (
        report,  # the MODEL report module (incidence calc), not viz.report
    )

    os.makedirs(out_dir, exist_ok=True)
    inc = report.incidence(base_tpi, reform_tpi, i_energy)
    w = np.asarray(inc["consumption_by_J"], dtype=float)
    J = len(w)
    lab = _labels(J)

    cib, pib = np.asarray(base_tpi["c_i"]), np.asarray(base_tpi["p_i"])  # (T,I,S,J),(T,I)
    spend = pib[0][:, None, None] * cib[0]                                # (I,S,J)
    share = (spend[i_energy] / spend.sum(axis=0)).mean(axis=0) * 100       # (J,) energy budget share %

    ncol = 3 if factor is not None else 2
    fig, axes = plt.subplots(1, ncol, figsize=(4.9 * ncol, 5.0),
                             gridspec_kw={"width_ratios": [1.12, 1.0, 1.12][:ncol]})
    fig.subplots_adjust(top=0.74, bottom=0.17, left=0.055, right=0.985, wspace=0.30)

    # (1) who bears it -- the incidence curve
    ax = axes[0]
    style.clean(ax)
    style.zero_line(ax)
    ax.plot(range(J), w, color="0.75", lw=1.2, zorder=1)
    ax.scatter(range(J), w, c=style.signed(w), s=110, zorder=3, edgecolor="white", linewidth=1.0)
    ax.set_xticks(range(J))
    ax.set_xticklabels(lab, rotation=30, ha="right")
    ax.set_ylabel("consumption change (%)")
    ax.set_title("Who's affected, by income group")
    ax.margins(y=0.16)  # headroom so the extreme-value labels clear the axis/tick labels
    jmin, jmax = int(np.argmin(w)), int(np.argmax(w))
    for j, va in ((jmin, "top" if w[jmin] < 0 else "bottom"),
                  (jmax, "bottom" if w[jmax] >= 0 else "top")):
        ax.annotate(f"{w[j]:+.2f}%", (j, w[j]), xytext=(0, 11 if va == "bottom" else -11),
                    textcoords="offset points", ha="center", va=va, fontsize=9.5,
                    fontweight="bold", color=GAIN if w[j] >= 0 else LOSS)

    # (2) the mechanism -- welfare vs baseline energy budget share
    ax = axes[1]
    style.clean(ax, grid="y")
    style.zero_line(ax)
    ax.scatter(share, w, c=style.signed(w), s=90, edgecolor="white", linewidth=1.0, zorder=3)
    sp = float(share.mean())
    ax.set_xlim(0, max(2.2, float(share.max()) * 1.5))
    ax.set_xlabel("baseline energy budget share (%)")
    ax.set_ylabel("consumption change (%)")
    ax.set_title("Welfare effect vs energy's share of spending")
    ax.annotate(
        f"energy is ~{sp:.1f}% of the baseline\nbudget, on average across groups",
        xy=(sp, float(np.median(w))), xytext=(0.045, 0.94), textcoords="axes fraction",
        fontsize=8.5, color=style.SUB, va="top", ha="left",
        arrowprops=dict(arrowstyle="->", color="#BBBBBB", lw=0.8))

    # (3) the dollar effect per household
    if factor is not None:
        cb, cr = np.asarray(base_tpi["c"]), np.asarray(reform_tpi["c"])   # (T,S,J)
        dC = (cr[:10].mean(axis=(0, 1)) - cb[:10].mean(axis=(0, 1))) * float(factor)
        ax = axes[2]
        style.clean(ax)
        style.zero_line(ax)
        ax.bar(range(J), dC, color=style.signed(dC), width=0.74, zorder=2)
        ax.set_xticks(range(J))
        ax.set_xticklabels(lab, rotation=30, ha="right")
        ax.set_ylabel("consumption change / household / year (approx.)")
        ax.set_title("How much per household")
        for j, v in enumerate(dC):
            ax.annotate(f"{v:+,.0f}", (j, v), xytext=(0, 4 if v >= 0 else -4),
                        textcoords="offset points", ha="center",
                        va="bottom" if v >= 0 else "top", fontsize=8, color=style.INK)
        ax.margins(y=0.16)

    style.title_block(fig, title=title,
                      subtitle="Welfare effect by income group, poorest to richest  ·  "
                               "(consumption-equivalent: the % change in lifetime spending that "
                               "leaves a household equally well off)",
                      source=style.source_line(note), kicker=kicker, top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def _waterfall(values, labels, title, subtitle, ylabel, out_path, note=None,
               kicker="channel decomposition", segments=None):
    """Bridge chart: each bar is the MARGINAL contribution of adding that channel, stacked on a
    running cumulative; diverging color by sign. A net marker closes the bridge. ``segments`` (optional)
    maps a bar index -> [(value, color, label), ...] that SUM to that bar's marginal, drawn as a
    stacked bar with a small legend -- e.g. the health bar split into mortality + morbidity parts."""
    segments = segments or {}
    marg, cum = _bridge(values)
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.17, left=0.11, right=0.95)
    style.clean(ax)
    style.zero_line(ax)
    for i, m in enumerate(marg):
        if i in segments:                              # stacked sub-parts that sum to this marginal
            base = cum[i]
            for val, color, lab in segments[i]:
                ax.bar(i, val, bottom=base, color=color, width=0.62, zorder=2,
                       edgecolor="white", linewidth=0.6)
                base += val
        else:
            ax.bar(i, m, bottom=cum[i], color=GAIN if m >= 0 else LOSS, width=0.62, zorder=2)
        if i < len(marg) - 1:
            ax.plot([i + 0.31, i + 1 - 0.31], [cum[i + 1], cum[i + 1]], color="0.6",
                    lw=0.8, zorder=1)
        ax.annotate(f"{m:+.3f}", (i, cum[i + 1]), textcoords="offset points",
                    xytext=(0, 5 if m >= 0 else -5), ha="center",
                    va="bottom" if m >= 0 else "top", fontsize=8.5, color=style.INK)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel(ylabel)
    ax.margins(x=0.06, y=0.22)  # headroom for the net label + any segment callout
    y0, y1 = ax.get_ylim()
    # Label the mortality/illness split DIRECTLY on the bar it belongs to, with a leader -- not a
    # global legend (which wrongly implies every bar is split, and its teal swatch reads like the
    # blue bars). seg_handles drives whether there is anything to call out.
    for i, segs in segments.items():
        ytxt = cum[i + 1] + 0.06 * (y1 - y0)
        ax.annotate("", xy=(i, cum[i + 1]), xytext=(i - 0.45, ytxt),
                    arrowprops=dict(arrowstyle="-", color="#BBBBBB", lw=0.8), zorder=4)
        for k, (val, color, lab) in enumerate(segs):
            ax.text(i - 0.45, ytxt + k * 0.052 * (y1 - y0), f"{lab} {val:+.3f}", color=color,
                    fontsize=8.5, fontweight="medium", ha="center", va="bottom", zorder=4)
    # Net effect shown IN the figure (top-left), not in the title.
    ax.text(0.015, 0.97, f"net {cum[-1]:+.3f}%", transform=ax.transAxes, fontsize=10.5,
            fontweight="bold", color=style.INK, va="top", ha="left")
    style.title_block(fig, title=title, subtitle=subtitle,
                      source=style.source_line(note), kicker=kicker, top=0.965)
    return style.save(fig, out_path)


def across_steps_waterfall(layered, out_dir, note=None):
    solved = [r for r in layered if "macro" in r]
    if len(solved) < 2:
        return []
    labels = [r["step"] for r in solved]
    yvals = [r["macro"]["Y"] for r in solved]
    # Split the health bar into mortality + morbidity sub-parts, if the run recorded the split.
    # mortality marginal = mortality-only-cumulative GDP − the previous step's GDP; morbidity is the
    # remainder of the combined health marginal (a sequential, exact split that sums to the bar).
    segments = {}
    for i, r in enumerate(solved):
        split = r.get("health_split")
        if split is not None and i > 0:
            mort_marg = split["mortality"] - yvals[i - 1]
            morb_marg = (yvals[i] - yvals[i - 1]) - mort_marg
            segments[i] = [(mort_marg, style.CATEGORICAL[2], "mortality"),
                           (morb_marg, style.CATEGORICAL[3], "illness")]
    saved = [_waterfall(yvals, labels,
                        "What each scenario adds to output, vs baseline",
                        "Contribution as each scenario is layered on  ·  first 10 years (2026-2035)",
                        "GDP change vs baseline (%)", os.path.join(out_dir, "waterfall_gdp.png"), note,
                        segments=segments)]
    # the poorest-group panel needs the per-group consumption split, which is dropped when the run has
    # no isolated energy good (the energy channels skipped) -- emit it only when every step carries it.
    if all("consumption_by_J" in r for r in solved):
        saved.append(_waterfall([r["consumption_by_J"][0] for r in solved], labels,
                                "What each scenario adds for the poorest group, vs baseline",
                                "Welfare effect for the poorest 25%  ·  first 10 years (2026-2035)",
                                "consumption change vs baseline (%)",
                                os.path.join(out_dir, "waterfall_poorest.png"), note))
    return saved


def macro_honest(layered, out_dir, ylim=0.5, note=None):
    """Macro aggregates across steps on a FIXED axis, so near-zero effects read as near-zero;
    lines direct-labeled at their right ends (no legend box)."""
    solved = [r for r in layered if "macro" in r]
    if not solved:
        return []
    steps = [r["step"] for r in solved]
    n = len(steps)
    fig, ax = plt.subplots(figsize=(7.8, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.17, left=0.10, right=0.90)
    style.clean(ax, left=True)
    ends = []
    for v, c in zip(["Y", "C", "K", "L"], style.CATEGORICAL):
        ys = [r["macro"].get(v) for r in solved]
        ax.plot(range(n), ys, marker="o", color=c, zorder=2)
        ends.append((n - 1, ys[-1], v, c))
    style.zero_line(ax)
    style.label_ends(ax, ends)
    ax.set_ylim(-ylim, ylim)
    ax.set_xlim(-0.3, n - 1 + 0.5)
    ax.set_xticks(range(n))
    ax.set_xticklabels(steps, rotation=15, ha="right")
    ax.set_ylabel("change vs baseline (%)")
    finite = [(abs(y), y, v) for (_x, y, v, _c) in ends if y is not None]
    if finite:
        _, mval, mvar = max(finite)
        ax.annotate(f"largest move: {mval:+.2f}% ({mvar})",
                    (0.015, 0.04), xycoords="axes fraction", fontsize=8.5, color=style.SUB, va="bottom")
    style.title_block(fig, title="The economy vs baseline (output, consumption, capital, labor)",
                      subtitle="Change vs baseline (%), fixed axis  ·  Y output, C consumption, K capital, L labor",
                      source=style.source_line(note), kicker="macro aggregates", top=0.965)
    return [style.save(fig, os.path.join(out_dir, "macro_honest.png"))]


def energy_physical(country, out_dir, *, illustrative=True):
    """CLEWS emissions, reform vs baseline (the transition's physical signal), lines
    direct-labeled and the avoided-emissions wedge called out. `illustrative` gates the
    "model units" disclosure (dropped once the emissions are calibrated to real tonnes)."""
    from oglink import signals

    units = " (model units)" if illustrative else ""

    os.makedirs(out_dir, exist_ok=True)
    try:
        eb = signals.emissions_by_year(country.scenario.base_dir, country)
        er = signals.emissions_by_year(country.scenario.reform_dir, country)
    except Exception as e:  # noqa: BLE001
        print(f"[figures] energy_physical skipped: {type(e).__name__}: {e}")
        return []
    fig, ax = plt.subplots(figsize=(7.8, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.15, left=0.11, right=0.88)
    style.clean(ax)
    erb = eb.reindex(er.index)
    ax.plot(eb.index, eb.values, color=style.MUTE, zorder=2)
    ax.plot(er.index, er.values, color=style.GAIN, zorder=3)
    ax.fill_between(er.index, erb.values, er.values, color=style.GAIN, alpha=0.12, zorder=1)
    style.label_ends(ax, [(eb.index[-1], eb.values[-1], "baseline", style.MUTE),
                          (er.index[-1], er.values[-1], "reform", style.GAIN)])
    ax.set_xlim(right=float(er.index[-1]) + (float(er.index[-1]) - float(er.index[0])) * 0.13)
    ax.set_ylabel(f"emissions ({country.co2_emission}{units})")
    avoided = float(np.nansum(erb.values - er.values))
    if np.isfinite(avoided) and abs(avoided) > 0:
        ymid = float(er.index[len(er) // 2])
        yv = float(np.nanmean([erb.values[len(er) // 2], er.values[len(er) // 2]]))
        word = "avoided" if avoided > 0 else "additional"
        ax.annotate(f"cumulative {word}\n≈ {abs(avoided):,.0f} {country.co2_emission}{units}",
                    (ymid, yv), xytext=(6, 26), textcoords="offset points",
                    fontsize=8.5, color=style.TEAL, fontweight="medium", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))
    style.title_block(fig, title="Emissions: baseline vs reform",
                      subtitle="Energy-system emissions over time, baseline vs reform",
                      source=style.source_line(), kicker="energy system", top=0.965)
    return [style.save(fig, os.path.join(out_dir, "emissions_path.png"))]


def og_default_outputs(base_dir, reform_dir, out_dir, start_year=None, plots=False):
    """OG-Core's own macro_table (always) + plot_all (only if plots=True -- most of its 31
    default plots are coincident-line noise for a coupled run, so off by default)."""
    from ogcore import output_tables as ot
    from ogcore.utils import safe_read_pickle

    os.makedirs(out_dir, exist_ok=True)
    try:
        bt = safe_read_pickle(os.path.join(base_dir, "TPI", "TPI_vars.pkl"))
        bp = safe_read_pickle(os.path.join(base_dir, "model_params.pkl"))
        rt = safe_read_pickle(os.path.join(reform_dir, "TPI", "TPI_vars.pkl"))
        rp = safe_read_pickle(os.path.join(reform_dir, "model_params.pkl"))
        ot.macro_table(bt, bp, reform_tpi=rt, reform_params=rp, var_list=["Y", "C", "K", "L", "r", "w"],
                       output_type="pct_diff", num_years=10, start_year=start_year or bp.start_year
                       ).to_csv(os.path.join(out_dir, "og_macro_table.csv"))
    except Exception as e:  # noqa: BLE001
        print(f"[figures] og macro_table skipped: {type(e).__name__}: {e}")
    if plots:
        from ogcore import output_plots as op
        try:
            op.plot_all(base_dir, reform_dir, os.path.join(out_dir, "og_plots"))
        except Exception as e:  # noqa: BLE001
            print(f"[figures] og plot_all skipped: {type(e).__name__}: {e}")
    return out_dir


# ============================== TRANSITION ==============================

MACRO_VARS = [("Y", "GDP", style.CATEGORICAL[0]), ("C", "consumption", style.CATEGORICAL[1]),
              ("K", "capital", style.CATEGORICAL[2]), ("L", "labor", style.CATEGORICAL[3])]


def _years(start_year, n):
    return np.arange(int(start_year), int(start_year) + int(n))


def _clamp_n(hz, base_tpi, reform_tpi, *vars_):
    """Plot horizon clamped to BOTH dicts' actual lengths for every variable plotted, so a
    shorter reform array can never make _pct_path slice mismatched lengths and crash."""
    lens = [len(np.asarray(d[v])) for v in vars_
            for d in (base_tpi, reform_tpi) if v in d]
    return min([int(hz)] + lens)


def _pct_path(base_tpi, reform_tpi, var, n):
    return style.pct_dev(np.asarray(reform_tpi[var], dtype=float)[:n],
                         np.asarray(base_tpi[var], dtype=float)[:n])


def _closure_window(params, start_year, default_n, *, tail=30):
    """Calendar year the OG-Core budget-closure rule begins (start_year + tG1) and a plot horizon
    that stops a modest tail past it -- long-run convergence (tG2) is centuries out and not worth
    plotting. Returns (closure_year or None, n_years)."""
    if params is None:
        return None, int(default_n)
    try:
        tG1 = int(np.atleast_1d(params.tG1).flat[0])
    except Exception:  # noqa: BLE001
        return None, int(default_n)
    return int(start_year) + tG1, min(int(default_n), tG1 + int(tail))


def _closure_line(ax, closure_year, yrs):
    """Dashed vertical marker where the budget-closure rule begins (only if within the span)."""
    if closure_year is None or not (yrs[0] <= closure_year <= yrs[-1]):
        return
    ax.axvline(closure_year, color=style.SUB, lw=0.9, ls=(0, (4, 3)), zorder=1.8)
    # White halo + high zorder so the label stays readable where a series peaks near the closure
    # year (the marker would otherwise sit right under it on several transition figures).
    ax.annotate("budget rule begins", (closure_year, ax.get_ylim()[1]), xytext=(4, -4),
                textcoords="offset points", fontsize=8, color=style.SUB, va="top", zorder=6,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85))


def macro_transition(base_tpi, reform_tpi, out_dir, *, start_year, note=None, n_years=80,
                     params=None, title="The economy over time, vs baseline (output, consumption, capital, labor)",
                     name="macro_transition"):
    """Y/C/K/L % deviation from baseline across the transition, calendar-year x-axis, lines
    direct-labeled at their right ends. The largest GDP deviation is marked -- the path can be
    several times the long-run (10-yr-mean) effect the snapshot figures report."""
    os.makedirs(out_dir, exist_ok=True)
    closure_year, hz = _closure_window(params, start_year, n_years)
    n = _clamp_n(hz, base_tpi, reform_tpi, *(v for v, _, _ in MACRO_VARS))
    yrs = _years(start_year, n)
    paths = {v: _pct_path(base_tpi, reform_tpi, v, n) for v, _, _ in MACRO_VARS}

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.085, right=0.86)
    style.clean(ax, left=True)
    ends = []
    for v, lab, c in MACRO_VARS:
        ax.plot(yrs, paths[v], color=c, lw=2.2, zorder=2)
        ends.append((yrs[-1], paths[v][-1], lab, c))
    style.zero_line(ax)
    # call out the largest GDP deviation (the dynamic the snapshot hides) -- by magnitude, so
    # the marker is honest whether the path runs above or below baseline
    y = paths["Y"]
    pk = int(np.nanargmax(np.abs(y)))
    ax.scatter([yrs[pk]], [y[pk]], s=46, color=style.CATEGORICAL[0], zorder=4,
               edgecolor="white", linewidth=1.0)
    ax.annotate(f"largest deviation {y[pk]:+.2f}% in {yrs[pk]}", (yrs[pk], y[pk]),
                xytext=(8, 12), textcoords="offset points", fontsize=9.5,
                fontweight="bold", color=style.CATEGORICAL[0])
    rng = float(np.nanmax([np.nanmax(np.abs(p)) for p in paths.values()]))
    # Nudge near-zero end-labels (e.g. capital/labor, which can both finish ~0) off the zero axis
    # and onto their own side, then de-collide with a generous gap so they don't stack and touch.
    off = 0.06 * rng
    ends = [(x, (off if y >= 0 else -off) if abs(y) < off else y, t, c) for (x, y, t, c) in ends]
    style.label_ends(ax, ends, min_gap=0.09 * rng)
    ax.set_xlim(yrs[0], yrs[-1] + (yrs[-1] - yrs[0]) * 0.12)
    ax.set_ylabel("change vs baseline (%)")
    _y0, _y1 = ax.get_ylim()                          # top headroom so the closure label clears
    ax.set_ylim(_y0, _y1 + 0.14 * (_y1 - _y0))        # the GDP-peak marker
    _closure_line(ax, closure_year, yrs)
    style.title_block(
        fig, title=title,
        subtitle=f"% change vs baseline, {yrs[0]}–{yrs[-1]}  ·  shows how the economy gets there over time",
        source=style.source_line(note), kicker="macro transition", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def fiscal_transition(base_tpi, reform_tpi, out_dir, *, start_year, note=None, n_years=80,
                      params=None, name="fiscal_transition"):
    """Debt/GDP and Revenue/GDP as LEVELS (baseline vs reform) across the transition -- the
    fiscal footprint of the reform. (Carbon/consumption-tax revenue is not recycled here, so
    the revenue line is a phantom-revenue diagnostic, flagged in the caption.)"""
    os.makedirs(out_dir, exist_ok=True)
    closure_year, hz = _closure_window(params, start_year, n_years)

    panels = [("D", "Debt / GDP", "government debt"),
              ("total_tax_revenue", "Revenue / GDP", "total tax revenue")]
    panels = [p for p in panels if p[0] in base_tpi and p[0] in reform_tpi]
    if not panels:
        return []
    n = _clamp_n(hz, base_tpi, reform_tpi, "Y", *(p[0] for p in panels))
    yrs = _years(start_year, n)

    def ratio(tpi, num):
        return 100.0 * np.asarray(tpi[num], float)[:n] / np.asarray(tpi["Y"], float)[:n]
    fig, axes = plt.subplots(1, len(panels), figsize=(4.9 * len(panels), 5.0))
    axes = np.atleast_1d(axes)
    fig.subplots_adjust(top=0.74, bottom=0.13, left=0.075, right=0.93, wspace=0.26)
    for ax, (var, ttl, desc) in zip(axes, panels):
        style.clean(ax, left=True)
        rb, rr = ratio(base_tpi, var), ratio(reform_tpi, var)
        ax.plot(yrs, rb, color=style.MUTE, lw=2.0, zorder=2)
        ax.plot(yrs, rr, color=style.CATEGORICAL[0], lw=2.2, zorder=3)
        ax.fill_between(yrs, rb, rr, color=style.CATEGORICAL[0], alpha=0.10, zorder=1)
        style.label_ends(ax, [(yrs[-1], rb[-1], "baseline", style.MUTE),
                              (yrs[-1], rr[-1], "reform", style.CATEGORICAL[0])],
                         min_gap=0.05 * (float(np.nanmax(np.r_[rb, rr])) - float(np.nanmin(np.r_[rb, rr])) or 1))
        ax.set_xlim(yrs[0], yrs[-1] + (yrs[-1] - yrs[0]) * 0.16)
        ax.set_title(f"{ttl}  ·  {desc}")
        ax.set_ylabel("% of GDP")
        _closure_line(ax, closure_year, yrs)
    style.title_block(
        fig, title="Government debt and revenue over time",
        subtitle="Debt and revenue as a share of GDP, baseline vs reform",
        source=style.source_line(note), kicker="fiscal paths", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def revenue_transition(base_tpi, reform_tpi, out_dir, *, start_year, note=None, n_years=80,
                       params=None, name="revenue_transition"):
    """Consumption-tax revenue (the carbon tax flows through it) as a share of GDP, baseline AND
    reform LEVELS across the transition -- not just the change -- so the absolute paths and the gap
    between them both read. Closure-rule marker; capped to the closure window."""
    if not all("cons_tax_revenue" in t and "Y" in t for t in (base_tpi, reform_tpi)):
        return []
    os.makedirs(out_dir, exist_ok=True)
    closure_year, hz = _closure_window(params, start_year, n_years)
    n = _clamp_n(hz, base_tpi, reform_tpi, "cons_tax_revenue", "Y")
    yrs = _years(start_year, n)

    def _share(tpi):  # revenue as % of GDP (a level, comparable across base/reform)
        rev = np.asarray(tpi["cons_tax_revenue"], dtype=float)[:n]
        gdp = np.asarray(tpi["Y"], dtype=float)[:n]
        return 100.0 * rev / np.where(gdp == 0, np.nan, gdp)

    rb, rr = _share(base_tpi), _share(reform_tpi)
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.10, right=0.88)
    style.clean(ax, left=True)
    ax.plot(yrs, rb, color=style.MUTE, lw=2.2, zorder=2)
    ax.plot(yrs, rr, color=style.CATEGORICAL[2], lw=2.4, zorder=3)
    ax.fill_between(yrs, rb, rr, color=style.CATEGORICAL[2], alpha=0.10, zorder=1)
    rng = float(np.nanmax(np.concatenate([rb, rr])) - np.nanmin(np.concatenate([rb, rr]))) or 1.0
    style.label_ends(ax, [(yrs[-1], rb[-1], "baseline", style.MUTE),
                          (yrs[-1], rr[-1], "reform", style.CATEGORICAL[2])], min_gap=0.08 * rng)
    ax.set_xlim(yrs[0], yrs[-1] + (yrs[-1] - yrs[0]) * 0.14)
    ax.set_ylabel("consumption-tax revenue (% of GDP)")
    _closure_line(ax, closure_year, yrs)
    style.title_block(
        fig, title="Consumption-tax revenue over time (incl. carbon)",
        subtitle=f"Revenue as a share of GDP, baseline vs reform, {yrs[0]}-{yrs[-1]}",
        source=style.source_line(note), kicker="carbon revenue", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def rates_transition(base_tpi, reform_tpi, out_dir, *, start_year, note=None, n_years=80,
                     params=None, name="rates_transition"):
    """Interest rate r and wage w as % deviation from baseline across the transition. Both are
    PRICES (r a rate, w a level), so % deviation is the comparable unit (not the ×100-of-a-wage-
    level artifact). The computed max |deviation| is shown in the subtitle."""
    have = [v for v in ("r", "w") if v in base_tpi and v in reform_tpi]
    if not have:
        return []
    os.makedirs(out_dir, exist_ok=True)
    closure_year, hz = _closure_window(params, start_year, n_years)
    n = _clamp_n(hz, base_tpi, reform_tpi, *have)
    yrs = _years(start_year, n)
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.10, right=0.88)
    style.clean(ax, left=True)
    style.zero_line(ax)
    labels = {"r": ("interest rate", style.CATEGORICAL[4]), "w": ("wage", style.CATEGORICAL[2])}
    ends, allv = [], []
    for v in ("r", "w"):
        if v not in have:
            continue
        d = _pct_path(base_tpi, reform_tpi, v, n)
        allv.append(d)
        lab, c = labels[v]
        ax.plot(yrs, d, color=c, lw=2.2, zorder=2)
        ends.append((yrs[-1], d[-1], lab, c))
    rng = float(np.nanmax([np.nanmax(np.abs(d)) for d in allv]))
    style.label_ends(ax, ends, min_gap=0.10 * rng)
    ax.set_xlim(yrs[0], yrs[-1] + (yrs[-1] - yrs[0]) * 0.14)
    ax.set_ylabel("change vs baseline (%)")
    _y0, _y1 = ax.get_ylim()                          # top headroom so the peak isn't clipped and
    ax.set_ylim(_y0, _y1 + 0.16 * (_y1 - _y0))        # the closure label clears the peak
    _closure_line(ax, closure_year, yrs)
    style.title_block(
        fig, title="Interest rates and wages over time",
        subtitle=f"Interest rate and wage, % change vs baseline  ·  largest change {rng:.2f}%",
        source=style.source_line(note), kicker="factor prices", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


_PUBINV_VARS = [("I_g", "public investment", style.CATEGORICAL[0]),
                ("K_g", "public capital", style.CATEGORICAL[2])]


def public_investment(base_tpi, reform_tpi, out_dir, *, start_year, note=None, n_years=80,
                      params=None, name="public_investment"):
    """Public investment (I_g) and public capital (K_g) as % deviation from baseline across the
    transition. Calendar-year x-axis, lines direct-labeled at their right ends, closure-rule
    marker, capped plot horizon. Scoped to the title subject -- the broader investment aggregates
    are deliberately omitted (their single-period outlier would compress these paths). Magnitudes
    are uncalibrated -- keep that caveat in the caption note. Returns [] if I_g/K_g are absent."""
    if not all(v in base_tpi and v in reform_tpi for v in ("I_g", "K_g")):
        return []
    os.makedirs(out_dir, exist_ok=True)
    closure_year, hz = _closure_window(params, start_year, n_years)
    n = _clamp_n(hz, base_tpi, reform_tpi, *(v for v, _, _ in _PUBINV_VARS))
    yrs = _years(start_year, n)
    vars_here = [(v, lab, c) for v, lab, c in _PUBINV_VARS
                 if v in base_tpi and v in reform_tpi]

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.10, right=0.84)
    style.clean(ax, left=True)
    style.zero_line(ax)
    ends, allv = [], []
    for v, lab, c in vars_here:
        d = _pct_path(base_tpi, reform_tpi, v, n)
        allv.append(d)
        ax.plot(yrs, d, color=c, lw=2.2, zorder=2)
        ends.append((yrs[-1], d[-1], lab, c))
    rng = float(np.nanmax([np.nanmax(np.abs(d)) for d in allv]))
    # Two converging end-labels can also land on the zero line; a generous min_gap nudges them
    # apart vertically and a non-zero floor keeps the gap usable even when both ends sit near 0.
    style.label_ends(ax, ends, min_gap=max(0.16 * rng, 0.08))
    ax.set_xlim(yrs[0], yrs[-1] + (yrs[-1] - yrs[0]) * 0.14)
    ax.set_ylabel("change vs baseline (%)")
    _y0, _y1 = ax.get_ylim()                          # top headroom so the closure label clears
    ax.set_ylim(_y0, _y1 + 0.14 * (_y1 - _y0))        # the steep public-investment rise
    _closure_line(ax, closure_year, yrs)
    style.title_block(
        fig, title="Public investment and public capital over time",
        subtitle=f"% change vs baseline, {yrs[0]}–{yrs[-1]}  ·  largest change {rng:.2f}%",
        source=style.source_line(note), kicker="public capital", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# ============================== ENERGY ==============================

_POWER_TECH_NAMES = {
    "NUSMR": "Nuclear (SMR)",
    "WON": "Onshore wind",
    "WOFF": "Offshore wind",
    "SPV": "Solar PV",
    "HYD": "Hydro",
    "NGCC": "Gas (combined cycle)",
    "NGGT": "Gas (turbine)",
    "COAL": "Coal",
    "OIL": "Oil",
    "BIO": "Biomass",
    "GEO": "Geothermal",
    "NUC": "Nuclear",
}


def _plain_tech_label(token: str) -> str:
    """Turn a raw CLEWS power-tech code into a plain name. Strips a leading country/power
    prefix (e.g. "PHL_POW_PP_") and any trailing variant suffix (e.g. "_T1"), then maps the
    remaining technology token to a plain name. Falls back to the cleaned token if the
    technology is not recognized."""
    cleaned = str(token).strip()
    # strip a leading country/power prefix: everything up to and including the last "PP_",
    # or failing that the conventional "<COUNTRY>_POW_" head.
    upper = cleaned.upper()
    if "PP_" in upper:
        cleaned = cleaned[upper.rindex("PP_") + len("PP_"):]
    elif "_POW_" in upper:
        cleaned = cleaned[upper.index("_POW_") + len("_POW_"):]
    # drop a trailing variant suffix (e.g. "_T1", "_1") so "WON_T1" maps on "WON"
    core = cleaned.split("_")[0] if "_" in cleaned else cleaned
    return _POWER_TECH_NAMES.get(core.upper(), cleaned.replace("_", " "))


def _energy_good_index(concordance):
    """The OG consumption good households buy as energy -- read from the PER-RUN concordance (the one
    the OG runner discovered + exported; the viz driver loads it from the run's baseline_meta.json),
    never hardcoded. Returns None when the country has no isolated energy good (so the caller degrades
    to no energy overlay rather than guessing an index)."""
    try:
        idx = getattr(concordance, "energy_good_index", None)
        return int(idx) if idx is not None else None
    except (TypeError, ValueError):
        return None


def _applied_energy_wedge(base_params, reform_params, i_e: int):
    """Recover the energy-price wedge the run actually applied to the OG energy good as the
    multiplicative reform/base ad-valorem ratio (1 + tau_reform) / (1 + tau_base) - 1, per
    period. The wedge is a reform/base price multiplier, directly comparable to the CLEWS cost
    ratio. Returns (wedge_path, is_flat) or (None, None) if tau_c is absent/misshaped."""
    try:
        tb = np.asarray(base_params.tau_c, dtype=float)
        tr = np.asarray(reform_params.tau_c, dtype=float)
    except Exception:  # noqa: BLE001
        return None, None
    if (tb.ndim != 2 or tr.ndim != 2 or i_e < 0
            or i_e >= tb.shape[1] or i_e >= tr.shape[1]):
        return None, None
    n = min(tb.shape[0], tr.shape[0])
    be, rf = tb[:n, i_e], tr[:n, i_e]
    wedge = (1.0 + rf) / np.where((1.0 + be) == 0, np.nan, (1.0 + be)) - 1.0
    # "flat" within numerical noise -> report it as the single constant the run applied
    finite = wedge[np.isfinite(wedge)]
    is_flat = bool(finite.size and (finite.max() - finite.min()) < 1e-4)
    return wedge, is_flat


def _gdp_musd(country):
    return float(getattr(country, "gdp_musd", np.nan))


def clews_signal_vs_applied(country, base_params, reform_params, out_dir, *, note=None,
                            concordance=None, illustrative=True, name="clews_signal_vs_applied"):
    """The real CLEWS energy-price cost ratio (reform/base electricity cost) over calendar years,
    with the flat proxy wedge the coupled run actually applied to the OG energy good overlaid.

    The CLEWS ratio comes from the curated 'Cost of electricity generation' workbook each scenario
    ships (signals.cost_of_electricity_ratio reading country.scenario dirs). The applied wedge is
    recovered from the run's tau_c on the energy good. Both are reform/base multipliers, so they
    share the y-axis (1.0 == parity). The headline run used an illustrative CONSTANT shock rather
    than the data path -- stated as fact in the caption; the gap reads off the two plotted lines
    and the computed numbers, never as a judgment. Returns [] if the CLEWS workbook is unreadable.
    """
    try:
        ratio = signals.cost_of_electricity_ratio(
            _cost_xlsx(country.scenario.base_dir), _cost_xlsx(country.scenario.reform_dir))
    except Exception:  # noqa: BLE001 -- no CLEWS dirs / workbook -> skip cleanly
        return []
    ratio = ratio.dropna()
    if ratio.empty:
        return []
    years = np.asarray(ratio.index, dtype=int)
    rv = np.asarray(ratio.values, dtype=float)

    i_e = _energy_good_index(concordance)
    wedge, is_flat = _applied_energy_wedge(base_params, reform_params, i_e) if i_e is not None else (None, None)
    applied_mult = (1.0 + float(np.nanmean(wedge))) if wedge is not None else None

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    fig.subplots_adjust(top=0.74, bottom=0.13, left=0.085, right=0.82)
    style.clean(ax, left=True)
    style.zero_line(ax, value=1.0)  # parity reference: reform == base

    # the real CLEWS signal -- the data path
    ax.plot(years, rv, color=style.CATEGORICAL[0], lw=2.4, zorder=3)
    rng = float(np.nanmax(rv) - np.nanmin(rv)) or 1.0
    # lift the end-label clear of the 1.0 parity reference when the ratio ends near parity, so the
    # solid reference line does not strike through the text
    _ylab = rv[-1] + (0.05 * rng if rv[-1] >= 1.0 else -0.05 * rng)
    ends = [(years[-1], _ylab, "energy model's path", style.CATEGORICAL[0])]

    # the flat applied wedge -- grey the proxy, color the signal
    if applied_mult is not None:
        ax.axhline(applied_mult, color=style.MUTE, lw=2.0, ls=(0, (5, 3)), zorder=2)
        # lift the end-label clear of its own dashed axhline so the line does not strike through it
        ends.append((years[-1], applied_mult + 0.03 * rng, "flat price this run used", style.MUTE))

    style.label_ends(ax, ends, min_gap=0.08 * rng)
    ax.set_xlim(years[0], years[-1] + (years[-1] - years[0]) * 0.14)
    ax.set_ylabel("energy price vs baseline (1.0 = no change)")

    # subtitle carries only COMPUTED numbers; direction/magnitude are derived, never asserted
    sub = (f"Energy-system price ratio (reform vs baseline) ranges {rv.min():.2f} to {rv.max():.2f} "
           f"(average {rv.mean():.2f}), {years[0]}–{years[-1]}")
    if applied_mult is not None:
        kind = "a constant" if is_flat else "a near-constant"
        sub += f"  ·  this run instead assumed {kind} energy price of {applied_mult:.2f}"
    cap = ("The flat price is the run's energy-good multiplier; this illustrative run used a flat "
           "shock, not the year-by-year energy-system path") if illustrative else None
    style.title_block(
        fig, title="Energy-price signal: what the energy model produced vs what this run assumed",
        subtitle=sub,
        source=style.source_line(note, extra=cap),
        kicker="energy price", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def capex_by_technology(country, out_dir, *, note=None, illustrative=True,
                        name="capex_by_technology"):
    """Cumulative reform-minus-base power-sector CapitalInvestment by technology, straight from the
    ENERGY MODEL (CLEWS CapitalInvestment exports) -- the investment the transition reallocates
    across the generation fleet. Diverging horizontal bars from zero, sorted by value, each labeled
    with its computed value. Power technologies are selected via country.is_power; magnitudes are
    model units with no deflator (gated by `illustrative`). Returns [] if the CapitalInvestment
    exports are unreadable, or skips technologies with a zero increment."""
    try:
        # signals exposes no public CLEWS-export finder; reuse its private _find (same locator
        # the channels use) rather than re-implement the glob here.
        mb = signals.read_clews_matrix(signals._find(country.scenario.base_dir, "CapitalInvestment"))
        mr = signals.read_clews_matrix(signals._find(country.scenario.reform_dir, "CapitalInvestment"))
    except Exception:  # noqa: BLE001
        return []

    def _cum(m):
        keep = [t for t in m.index if country.is_power(t)]
        return m.loc[keep].sum(axis=1) if keep else m.sum(axis=1).iloc[:0]

    cb, cr = _cum(mb), _cum(mr)
    techs = sorted(set(cb.index) | set(cr.index))
    diff = {t: float(cr.get(t, 0.0)) - float(cb.get(t, 0.0)) for t in techs}
    diff = {t: v for t, v in diff.items() if abs(v) > 1e-9}  # drop unchanged technologies
    if not diff:
        return []
    items = sorted(diff.items(), key=lambda kv: kv[1])  # ascending -> negatives at bottom
    labels = [t for t, _ in items]
    vals = np.asarray([v for _, v in items], dtype=float)

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.8, max(3.9, 0.5 * len(vals) + 2.7)))
    fig.subplots_adjust(top=0.80, bottom=0.22, left=0.36, right=0.92)
    style.clean(ax, left=False, grid="x")
    style.zero_line(ax, axis="x")
    ypos = np.arange(len(vals))
    ax.barh(ypos, vals, color=style.signed(vals), zorder=2, height=0.72)
    ax.set_yticks(ypos)
    ax.set_yticklabels([_plain_tech_label(t) for t in labels], fontsize=9)
    span = float(np.nanmax(np.abs(vals))) or 1.0
    for y, v in zip(ypos, vals):
        off = 0.012 * span * (1 if v >= 0 else -1)
        ax.annotate(f"{v:+,.0f}", (v + off, y), va="center",
                    ha="left" if v >= 0 else "right", fontsize=9,
                    color=style.GAIN if v >= 0 else style.LOSS)
    # x-limits from the actual data extremes (not symmetric ±max|val|, which leaves a dead
    # half-axis when the increments lean one way) plus a margin for the end labels; always
    # include zero so the diverging bars read against the zero reference.
    lo = float(min(vals.min(), 0.0))
    hi = float(max(vals.max(), 0.0))
    margin = 0.28 * span
    ax.set_xlim(lo - margin, hi + margin)
    units = " (model units)" if illustrative else ""
    try:
        yrs = [int(c) for c in mb.columns]
        span = f", cumulated over {min(yrs)}-{max(yrs)}"
    except Exception:  # noqa: BLE001 -- columns aren't year-like; omit the window
        span = ""
    ax.set_xlabel(f"change in capital investment{units}")
    extra = ("Model units, not real pesos -- read the direction and relative size, not the absolute "
             "amount") if illustrative else None
    style.title_block(
        fig, title="Change in power-sector investment, by technology (energy model)",
        subtitle=f"Energy-model investment, reform vs baseline, across {len(vals)} power "
                 f"technologies{span}  ·  net {vals.sum():+,.0f}{units}",
        source=style.source_line(note, extra=extra),
        kicker="investment · power sector", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def channel_inputs_over_time(country, base_tpi, out_dir, *, note=None, illustrative=True,
                             name="channel_inputs"):
    """Small multiples (shared calendar x-axis) of the time-varying signals the ENERGY MODEL hands
    to the economy -- i.e. how the scenario is wired together: the energy-price cost ratio, the
    power-capex increment (as % of GDP), and the emissions gap (reform/base). A setup/methods
    figure, not a result. Each panel is a neutral description; where a channel collapses a path to
    a scalar before feeding OG, that fact is annotated. Skipped panels degrade gracefully; [] if
    none can be built."""
    gdp = _gdp_musd(country)
    panels = []  # (title, years, values, baseline_value, color, annotate-fn)

    # energy-price cost ratio (reform / base); parity reference at 1.0
    try:
        r = signals.cost_of_electricity_ratio(
            _cost_xlsx(country.scenario.base_dir), _cost_xlsx(country.scenario.reform_dir)).dropna()
        if not r.empty:
            yrs = np.asarray(r.index, dtype=int)
            v = np.asarray(r.values, dtype=float)
            panels.append(("Energy price, reform vs baseline", yrs, v, 1.0,
                           style.CATEGORICAL[0],
                           f"range {v.min():.2f}–{v.max():.2f}"))
    except Exception:  # noqa: BLE001
        pass

    # power-capex increment as % of GDP (reform - base); zero reference
    try:
        inc = signals.power_capex_increment(
            country.scenario.base_dir, country.scenario.reform_dir, country, public_only=False)
        if not inc.empty and np.isfinite(gdp) and gdp > 0:
            yrs = np.asarray(inc.index, dtype=int)
            v = 100.0 * np.asarray(inc.values, dtype=float) / gdp
            panels.append(("Change in power-sector investment, % of GDP", yrs, v, 0.0,
                           style.CATEGORICAL[3],
                           f"sum over {yrs[0]}–{yrs[-1]}: {v.sum():+.2f}% of GDP"))
    except Exception:  # noqa: BLE001
        pass

    # emissions gap (reform / base); parity reference at 1.0
    try:
        er = signals.emissions_ratio(
            country.scenario.base_dir, country.scenario.reform_dir, country).dropna()
        if not er.empty:
            yrs = np.asarray(er.index, dtype=int)
            v = np.asarray(er.values, dtype=float)
            panels.append(("Emissions, reform vs baseline", yrs, v, 1.0,
                           style.CATEGORICAL[2],
                           f"average {v.mean():.2f}"))
    except Exception:  # noqa: BLE001
        pass

    if not panels:
        return []

    os.makedirs(out_dir, exist_ok=True)
    # shared calendar x-axis across the panels
    xlo = min(int(p[1][0]) for p in panels)
    xhi = max(int(p[1][-1]) for p in panels)
    fig, axes = plt.subplots(len(panels), 1, sharex=True,
                             figsize=(8.4, 2.4 * len(panels) + 1.6))
    axes = np.atleast_1d(axes)
    fig.subplots_adjust(top=0.82, bottom=0.10, left=0.10, right=0.93, hspace=0.42)
    for ax, (ttl, yrs, v, base_val, color, ann) in zip(axes, panels):
        style.clean(ax, left=True)
        style.zero_line(ax, value=base_val)
        ax.plot(yrs, v, color=color, lw=2.2, zorder=3)
        if base_val == 0.0:  # a flow: shade from the zero reference
            ax.fill_between(yrs, base_val, v, color=color, alpha=0.10, zorder=1)
        ax.set_title(ttl)
        ax.set_xlim(xlo, xhi)
        # place the annotation where the series is NOT: if the line ends in the upper half of
        # its range, drop the label to the bottom; if it ends low, lift it to the top. Keeps it
        # clear of a series that plunges or climbs at the right edge.
        vmin, vmax = float(np.nanmin(v)), float(np.nanmax(v))
        vspan = (vmax - vmin) or 1.0
        ends_high = (float(v[-1]) - vmin) / vspan >= 0.5
        ay, ava = (0.06, "bottom") if ends_high else (0.94, "top")
        # White halo + high zorder so a mid-panel dip or spike crossing the label does not strike
        # through it (the end-based placement above can't dodge an interior peak).
        ax.annotate(ann, (0.985, ay), xycoords="axes fraction", ha="right", va=ava,
                    fontsize=8.5, color=style.SUB, zorder=6,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    axes[-1].set_xlabel("year")
    extra = ("A scenario may reduce a year-by-year path to a single number (e.g. a flat price shock "
             "or a 10-year average) before it enters the economic model") if illustrative else None
    style.title_block(
        fig, title="How the scenario is built: the signals the energy model hands to the economy",
        subtitle="The inputs the energy model feeds into the economy, over time",
        source=style.source_line(note, extra=extra),
        kicker="scenario setup · energy model to economy", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# ============================== HEALTH ==============================

MORT, MORB = style.CATEGORICAL[2], style.CATEGORICAL[3]


def gbd_age_profiles(csv_path, location, year, out_dir, *, note=None, work_lo=15, work_hi=65,
                     name="health_age_profiles"):
    """Mortality h(s) and morbidity g(s) age profiles from the IHME GBD export (the exact builder
    the channel uses), as peak-1 relative shapes over single ages. Shades the working-age band so
    the deaths-vs-disability contrast by age is legible."""
    gbd_src = (f"Source: IHME GBD {year}, ambient particulate-matter burden, "
               f"{location} · author's calculations")
    hs = health_profile.build_profile_from_gbd(csv_path, location, year,
                                               key_col="cause_name", key_value="All causes")
    gs = health_profile.build_morbidity_profile_from_gbd(csv_path, location, year)
    ages = np.arange(len(hs))
    os.makedirs(out_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.08, right=0.86)
    style.clean(ax)
    ax.axvspan(work_lo, work_hi, color="0.90", zorder=0)
    ax.plot(ages, hs, color=MORT, lw=2.4, zorder=3)
    ax.plot(ages[:len(gs)], gs, color=MORB, lw=2.4, zorder=3)
    style.label_ends(ax, [(ages[-1], hs[-1], "death risk", MORT),
                          (len(gs) - 1, gs[-1], "illness risk", MORB)], min_gap=0.07)
    # working-age contrast: morbidity vs mortality at the band midpoint
    mid = (work_lo + work_hi) // 2
    ax.annotate(f"at age {mid}, disability is ~{gs[mid] / max(hs[mid], 1e-9):.0f}× the death risk",
                xy=(mid, gs[mid]), xytext=(0.04, 0.93), textcoords="axes fraction",
                fontsize=8.5, color=style.SUB, va="top", ha="left",
                arrowprops=dict(arrowstyle="->", color="#BBBBBB", lw=0.8))
    ax.annotate("working ages", (mid, 0.02), ha="center", va="bottom", fontsize=8.5,
                color=style.MUTE)
    ax.set_xlim(0, ages[-1] + 8)
    ax.set_ylim(0, 1.08)
    ax.set_xlabel("age")
    ax.set_ylabel("attributable rate by age (peak = 1)")
    style.title_block(
        fig, title="Air-pollution death and disability rates, by age",
        subtitle="PM2.5 air-pollution death and illness rates by age  ·  each curve is scaled to its own peak, so this shows the age pattern, not the relative size of death vs illness risk",
        source=style.source_line(note, base=gbd_src), kicker="health: age profiles", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def mortality_by_age(base_params, reform_params, out_dir, *, note=None, retire_age=None,
                     name="health_mortality_by_age"):
    """Age distribution of the reform's avoided mortality, from the solved SS survival rates:
    avoided deaths at age a ∝ (rho_base - rho_reform) × population share, with the retirement age
    marked. retire_age defaults to the model's own retirement age."""
    if retire_age is None:
        retire_age = style.retire_age(base_params)
    E, S = int(base_params.E), int(base_params.S)
    rho_b = np.asarray(base_params.rho, float)[-1]
    rho_r = np.asarray(reform_params.rho, float)[-1]
    omega = np.asarray(base_params.omega_SS, float)
    ages = E + np.arange(S)
    avoided = np.maximum(rho_b - rho_r, 0.0) * omega   # ∝ avoided deaths by age
    tot = avoided.sum()
    if tot <= 0:
        return []
    dist = 100.0 * avoided / tot                       # % of avoided deaths by age
    peak_age = int(ages[int(np.argmax(dist))])

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.085, right=0.95)
    style.clean(ax)
    ax.bar(ages, dist, width=0.92, color=MORT, zorder=2)
    if retire_age is not None:                                   # mark retirement + split only if known
        work_share = float(dist[ages < retire_age].sum())
        ax.axvspan(ages[0], retire_age, color="0.90", zorder=0)
        ax.axvline(retire_age, color=style.INK, lw=1.0, ls=(0, (4, 3)), zorder=3)
        ax.annotate(f"retirement ({retire_age})", (retire_age, ax.get_ylim()[1] * 0.92),
                    xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=style.SUB, va="top")
        ax.annotate(f"{work_share:.0f}% working-age · {100 - work_share:.0f}% retired",
                    (ages[0] + 2, np.max(dist) * 0.82), fontsize=9, color=style.SUB, va="top")
    ax.set_xlim(ages[0] - 1, ages[-1] + 1)
    ax.set_xlabel("age")
    ax.set_ylabel("share of total avoided deaths, by age (bars sum to 100%)")
    style.title_block(
        fig, title=f"Deaths avoided, by age (peaks near {peak_age})",
        subtitle="Where the reform's avoided deaths fall, by age (from solved survival rates)",
        source=style.source_line(note), kicker="health: avoided mortality", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def morbidity_by_age(base_params, reform_params, out_dir, *, note=None, retire_age=None,
                     work_lo=None, name="health_morbidity_by_age"):
    """Companion to mortality_by_age, on the morbidity side of the health channel: the age
    distribution of the reform's effective-labor change, from the solved e(t,s,j) profile.
    For a near-term transition row we lambda-weight e over the J income groups, take
    (e_reform - e_base) by age, and render each age's share of the total change as bars, with
    the working-age band shaded and the retirement age marked. retire_age defaults to the
    model's own retirement age; the working-age share is shown as a computed number."""
    if retire_age is None:
        retire_age = style.retire_age(base_params)
    E, S = int(base_params.E), int(base_params.S)
    e_b, e_r = getattr(base_params, "e", None), getattr(reform_params, "e", None)
    if e_b is None or e_r is None:                       # degrade gracefully if the field is absent
        return []
    eb = np.asarray(e_b, float)
    er = np.asarray(e_r, float)
    if eb.ndim != 3 or er.ndim != 3 or eb.shape != er.shape:
        return []
    lam = np.asarray(base_params.lambdas, float).ravel()
    if lam.shape[0] != eb.shape[2]:                      # fall back to equal weights if mismatched
        lam = np.full(eb.shape[2], 1.0 / eb.shape[2])

    def _by_age(arr_t):                                  # lambda-weight over J -> per-age effective labor
        return (arr_t * lam[None, :]).sum(axis=1)

    # pick a near-term row that actually carries the uplift (t=0 can be pre-phase-in / all zero)
    T = eb.shape[0]
    t = 0
    for k in range(T):
        if not np.allclose(_by_age(er[k]), _by_age(eb[k])):
            t = k
            break
    delta = _by_age(er[t]) - _by_age(eb[t])              # change in effective labor by age
    ages = E + np.arange(S)
    float(delta.sum())
    tot = float(np.abs(delta).sum())
    if tot <= 0:
        return []
    dist = 100.0 * delta / tot                           # % of total |effective-labor change| by age
    year = int(getattr(base_params, "start_year", 0) or 0) + t

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.085, right=0.95)
    style.clean(ax)
    style.zero_line(ax)                                  # change can be signed by age
    ax.bar(ages, dist, width=0.92, color=style.signed(dist, gain=MORB, loss=style.LOSS), zorder=2)
    if retire_age is not None:                           # mark retirement + working-age split only if known
        if work_lo is None:
            work_lo = ages[0]
        work_share = float(dist[(ages >= work_lo) & (ages < retire_age)].sum())
        ax.axvspan(work_lo, retire_age, color="0.90", zorder=0)
        ax.axvline(retire_age, color=style.INK, lw=1.0, ls=(0, (4, 3)), zorder=3)
        ax.annotate(f"retirement ({retire_age})", (retire_age, ax.get_ylim()[1] * 0.99),
                    xytext=(-6, 0), textcoords="offset points", fontsize=8.5, color=style.SUB,
                    va="top", ha="right",
                    bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85))
        ax.annotate(f"{work_share:.0f}% of the change lands on working-age people",
                    (ages[0] + 1, ax.get_ylim()[1] * 0.90), fontsize=9, color=style.SUB, va="top")
        # label the peak bar so the largest labeled magnitude sits on the visual mass
        peak_i = int(np.argmax(np.abs(dist)))
        peak_age = int(ages[peak_i])
        peak_share = float(dist[peak_i])
        ax.annotate(f"peak age {peak_age}: {peak_share:+.0f}%",
                    (peak_age, dist[peak_i]),
                    xytext=(0, 8 if dist[peak_i] >= 0 else -8), textcoords="offset points",
                    ha="center", va="bottom" if dist[peak_i] >= 0 else "top",
                    fontsize=8.5, color=style.SUB)
    ax.set_xlim(ages[0] - 1, ages[-1] + 1)
    ax.set_xlabel("age")
    ax.set_ylabel("share of the productivity change, by age (%)")
    yr_txt = f"transition year {year}" if year else f"transition row t={t}"
    style.title_block(
        fig, title="Where the reform changes worker productivity, by age",
        subtitle=f"Worker-productivity change by age, averaged across income groups  ·  {yr_txt}  ·  the model assigns productivity at all ages but only working ages supply labor, so a post-retirement peak does not lift output",
        source=style.source_line(note), kicker="health: morbidity", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def gdp_split(layered, out_dir, *, prev_step="+ carbon", health_step="+ health", note=None,
              illustrative=True, name="health_gdp_split"):
    """Standalone of the waterfall's health segment: the health channel's marginal GDP, split into
    its mortality and morbidity parts (a clean standalone of the waterfall's health bar).
    `illustrative` gates the "bar values are illustrative" disclosure."""
    by = {r.get("step"): r for r in layered}
    if health_step not in by or prev_step not in by or "health_split" not in by[health_step]:
        return []
    prevY = by[prev_step]["macro"]["Y"]
    split = by[health_step]["health_split"]
    mort = split["mortality"] - prevY
    morb = (split["combined"] - prevY) - mort
    vals = [mort, morb]
    labs = ["mortality", "morbidity"]

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.6, 5.1))
    fig.subplots_adjust(top=0.74, bottom=0.18, left=0.15, right=0.95)
    style.clean(ax)
    style.zero_line(ax)
    bars = ax.bar([0, 1], vals, width=0.56, color=[MORT, MORB], zorder=2)
    for x, v, b in zip([0, 1], vals, bars):
        ax.annotate(f"{v:+.4f}%", (x, v), xytext=(0, 6 if v >= 0 else -6),
                    textcoords="offset points", ha="center", va="bottom" if v >= 0 else "top",
                    fontsize=11, fontweight="bold", color=style.INK)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(labs)
    ax.margins(y=0.22)
    ax.set_ylabel("marginal contribution to GDP (%)")
    # Mechanism note in the bottom margin (figure coords), clear of the source line.
    illus = "  Bar values are illustrative." if illustrative else ""
    fig.text(0.5, 0.055,
             "fewer deaths means more retirees -- people who consume but no longer supply labor --\n"
             "so the mortality channel's measured-GDP contribution can be negative." + illus,
             ha="center", va="bottom", fontsize=8.0, color=style.SUB)
    style.title_block(
        fig, title="Health channel's effect on GDP: from fewer deaths vs from less illness",
        subtitle=f"GDP contribution from the health channel  ·  net {mort + morb:+.4f}%",
        source=style.source_line(note), kicker="health: GDP split", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# ============================== WELFARE ==============================

_BEQ_NOTE = "lifetime CEV (consumption + labor felicity; warm-glow bequest omitted, second-order)"


class _Felicity:
    """OG-Core household felicity + per-period weights, pulled from a model_params object."""

    def __init__(self, p):
        self.sigma = float(p.sigma)
        self.g_y = float(p.g_y)
        self.b_ellipse = float(p.b_ellipse)
        self.upsilon = float(p.upsilon)
        self.ltilde = float(p.ltilde)
        self.beta = np.asarray(p.beta, float).ravel()
        self.S = int(p.S)

    def labor_disutil(self, n):
        x = np.clip(np.asarray(n, float) / self.ltilde, 0.0, 1.0 - 1e-9)
        return self.b_ellipse * (1.0 - (1.0 - x ** self.upsilon) ** (1.0 / self.upsilon))

    def u_c(self, c):
        c = np.maximum(np.asarray(c, float), 1e-12)
        s = self.sigma
        return np.log(c) if abs(1.0 - s) < 1e-9 else c ** (1.0 - s) / (1.0 - s)

    def weights(self, rho, j):
        """W_s = (β_j e^{g_y(1-σ)})^s · cumulative survival to age s."""
        rho = np.asarray(rho, float)
        L = len(rho)
        surv = np.concatenate([[1.0], np.cumprod(1.0 - rho)[:-1]])
        disc = (self.beta[j] * np.exp(self.g_y * (1.0 - self.sigma))) ** np.arange(L)
        return disc * surv

    def V(self, c, n, chi_n, rho, j, phi=0.0):
        W = self.weights(rho, j)
        return float(np.sum(W * (self.u_c((1.0 + phi) * c) - np.asarray(chi_n, float) * self.labor_disutil(n))))

    def cev(self, base, reform, chi_n, rho_b, rho_r, j):
        """Solve V_base((1+φ)·c) = V_reform for φ (the CEV). base/reform are (c, n) tuples."""
        v_ref = self.V(reform[0], reform[1], chi_n, rho_r, j)
        f = lambda phi: self.V(base[0], base[1], chi_n, rho_b, j, phi) - v_ref
        try:
            return brentq(f, -0.99, 20.0, xtol=1e-10)
        except (ValueError, RuntimeError):
            return np.nan


def _ss_felicity(base_ss, reform_ss, base_params, reform_params):
    """Shared steady-state CEV preamble: a _Felicity built on the base params, the base/reform
    (c, n) SS arrays, the SS row of chi_n, and the SS bequest/survival rows for each scenario.
    Returns (fe, cb, nb, cr, nr, chi, rho_b, rho_r)."""
    fe = _Felicity(base_params)
    cb, nb = np.asarray(base_ss["c"], float), np.asarray(base_ss["n"], float)      # (S, J)
    cr, nr = np.asarray(reform_ss["c"], float), np.asarray(reform_ss["n"], float)
    chi = np.asarray(base_params.chi_n, float)[-1]                                  # SS row (S,)
    rho_b = np.asarray(base_params.rho, float)[-1]
    rho_r = np.asarray(reform_params.rho, float)[-1]
    return fe, cb, nb, cr, nr, chi, rho_b, rho_r


def cev_by_group(base_ss, reform_ss, base_params, reform_params, out_dir, *, note=None,
                 name="welfare_cev_by_group"):
    """Steady-state lifetime CEV by lifetime-income group -- the long-run welfare effect. Read it
    against the incidence_hero's consumption proxy: the proxy is near-term and cross-sectional,
    while CEV is the proper long-run lifetime-welfare measure."""
    fe, cb, nb, cr, nr, chi, rho_b, rho_r = _ss_felicity(base_ss, reform_ss, base_params, reform_params)
    J = cb.shape[1]
    cev = 100.0 * np.array([fe.cev((cb[:, j], nb[:, j]), (cr[:, j], nr[:, j]),
                                   chi, rho_b, rho_r, j) for j in range(J)])
    lab = _labels(J, np.asarray(base_params.lambdas, float).ravel())

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.8, 5.1))
    fig.subplots_adjust(top=0.76, bottom=0.19, left=0.10, right=0.95)
    style.clean(ax)
    style.zero_line(ax)
    ax.bar(range(J), cev, width=0.66, color=style.signed(cev), zorder=2)
    for j, v in enumerate(cev):
        ax.annotate(style.signed_pct(v, cev), (j, v), xytext=(0, -11 if v < 0 else 6),
                    textcoords="offset points", ha="center", va="top" if v < 0 else "bottom",
                    fontsize=9, fontweight="bold", color=style.LOSS if v < 0 else style.GAIN)
    ax.set_xticks(range(J))
    ax.set_xticklabels(lab, rotation=30, ha="right")
    ax.margins(y=0.20)
    ax.set_ylabel("Lifetime welfare effect (%)")
    fig.text(0.045, 0.055,
             "Note: carbon-tax revenue is not returned to households in this run; "
             "a design that returned it would change these results.",
             fontsize=8.5, color=style.SUB, ha="left", va="bottom", wrap=True)
    style.title_block(
        fig, title="Lifetime welfare effect by income group",
        subtitle=f"By income group, poorest to richest (negative = worse off)  ·  consumption-equivalent: "
                 f"the % of lifetime spending that leaves a household equally well off  ·  mean {style.signed_pct(np.nanmean(cev), cev)}",
        source=style.source_line(note, extra=_BEQ_NOTE),
        kicker="welfare: CEV by group", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def cev_decomposition(base_ss, reform_ss, base_params, reform_params, out_dir, *, note=None,
                      name="welfare_cev_decomposition"):
    """Steady-state lifetime CEV by income group, split into the channel it travels through.
    The consumption-only partial CEV holds LABOR n at baseline and lets only c move to reform;
    the labor-only partial CEV holds c at baseline and lets only n move. Each is a separate
    nonlinear root-find on the consumption-scaling φ that equates baseline felicity to the
    channel-shifted felicity, so the two partials do NOT add up to the full CEV -- they read as
    'how much of the welfare move would this channel deliver on its own'. Grouped bars per group,
    sign-colored by the computed value."""
    fe, cb, nb, cr, nr, chi, rho_b, rho_r = _ss_felicity(base_ss, reform_ss, base_params, reform_params)
    J = cb.shape[1]
    # Consumption channel: reform c, baseline n.  Labor channel: baseline c, reform n.  Each is
    # solved by the same root-find as the full CEV, just with the relevant reform component swapped.
    cev_c = 100.0 * np.array([fe.cev((cb[:, j], nb[:, j]), (cr[:, j], nb[:, j]),
                                     chi, rho_b, rho_r, j) for j in range(J)])
    cev_n = 100.0 * np.array([fe.cev((cb[:, j], nb[:, j]), (cb[:, j], nr[:, j]),
                                     chi, rho_b, rho_r, j) for j in range(J)])
    lab = _labels(J, np.asarray(base_params.lambdas, float).ravel())

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.1))
    fig.subplots_adjust(top=0.72, bottom=0.19, left=0.10, right=0.95)
    style.clean(ax)
    style.zero_line(ax)
    x = np.arange(J)
    bw = 0.38
    # spending channel: solid, sign-colored.  work channel: same sign-color but hatched, so the
    # two read apart by FILL (named in the legend) while color still encodes only the sign.
    ax.bar(x - bw / 2, cev_c, width=bw, color=style.signed(cev_c), zorder=2,
           edgecolor="white", linewidth=0.6)
    ax.bar(x + bw / 2, cev_n, width=bw, color=style.signed(cev_n), zorder=2,
           edgecolor="white", linewidth=0.6, hatch="////")
    allcev = np.concatenate([cev_c[np.isfinite(cev_c)], cev_n[np.isfinite(cev_n)]])  # one shared precision
    for off, vals in ((-bw / 2, cev_c), (bw / 2, cev_n)):
        for j, v in enumerate(vals):
            if not np.isfinite(v):
                continue
            ax.annotate(style.signed_pct(v, allcev, unit=""), (x[j] + off, v),
                        xytext=(0, -10 if v < 0 else 5),
                        textcoords="offset points", ha="center", va="top" if v < 0 else "bottom",
                        fontsize=9, fontweight="bold", color=style.LOSS if v < 0 else style.GAIN)
    # A two-swatch legend ABOVE the plot states the fill convention outright (solid = spending,
    # hatched = work), so the chart reads without the caption. Placed above the axes it never
    # lands on the bars regardless of their sign; grey swatches carry the PATTERN only, while the
    # bar color still encodes gain/loss.
    legend_handles = [Patch(facecolor=style.MUTE, edgecolor="white", label="spending channel"),
                      Patch(facecolor=style.MUTE, edgecolor="white", hatch="////", label="work channel")]
    ax.legend(handles=legend_handles, loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=2,
              frameon=False, fontsize=9.5, handlelength=1.5, handleheight=1.3,
              columnspacing=1.6, borderaxespad=0.3)
    ax.set_xticks(x)
    ax.set_xticklabels(lab, rotation=30, ha="right")
    ax.margins(y=0.20)
    ax.set_ylabel("lifetime welfare effect, by channel (%)")
    fin_c, fin_n = cev_c[np.isfinite(cev_c)], cev_n[np.isfinite(cev_n)]
    parts = []
    if fin_c.size:
        parts.append(f"spending mean {style.signed_pct(np.mean(fin_c), allcev)}")
    if fin_n.size:
        parts.append(f"work mean {style.signed_pct(np.mean(fin_n), allcev)}")
    means = "  ·  ".join(parts)
    work_mean = float(np.mean(fin_n)) if fin_n.size else float("nan")
    work_note = ("Note: the work-channel effect is about "
                 f"{style.signed_pct(work_mean, allcev)}, so its bars sit close to zero."
                 if np.isfinite(work_mean) else
                 "Note: the work-channel effect sits close to zero, so its bars are hard to see.")
    fig.text(0.045, 0.055, work_note, fontsize=8.5, color=style.SUB, ha="left", va="bottom", wrap=True)
    style.title_block(
        fig, title="Lifetime welfare effect by income group: spending vs work",
        subtitle="Each channel's welfare effect on its own; the two don't add up to the full effect "
                 "because they interact"
                 + (f"  ·  {means}" if means else "") + "  ·  negative = worse off",
        source=style.source_line(note, extra=_BEQ_NOTE),
        kicker="welfare: CEV decomposition", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def cev_by_age(base_tpi, reform_tpi, base_params, reform_params, out_dir, *, note=None,
               max_age=80, name="welfare_cev_by_age"):
    """Remaining-lifetime CEV for each cohort alive at the reform, by current age -- who, among
    people alive today, bears the cost. λ-weighted across income groups, with the group range as a
    band. Capped at ``max_age``: the extreme-old remaining-lifetime CEV is numerically ill-
    conditioned (a near-zero remaining-life utility blows up the ratio)."""
    fe = _Felicity(base_params)
    cB, nB = np.asarray(base_tpi["c"], float), np.asarray(base_tpi["n"], float)     # (T, S, J)
    cR, nR = np.asarray(reform_tpi["c"], float), np.asarray(reform_tpi["n"], float)
    chi_t = np.asarray(base_params.chi_n, float)                                    # (T+S, S)
    rhoB, rhoR = np.asarray(base_params.rho, float), np.asarray(reform_params.rho, float)
    lam = np.asarray(base_params.lambdas, float).ravel()
    S, E, J = fe.S, int(base_params.E), cB.shape[2]
    a_max = min(int(max_age) - E, S - 20)                                           # ≥20 periods left

    def diag(arr, a, j):    # cohort aged index a at t=0: ages a..S-1 over times 0..S-1-a
        return np.array([arr[t, a + t, j] for t in range(S - a)])

    max_cev = 0.05  # real signal is ~0.3%; |CEV|>5% is a root-find blow-up (e.g. at the labor=0
    #                 retirement kink or a near-zero remaining-life utility), not an economic result
    ages, cev_w, cev_lo, cev_hi = [], [], [], []
    for a in range(a_max + 1):
        chi = np.array([chi_t[t, a + t] for t in range(S - a)])
        rb = np.array([rhoB[t, a + t] for t in range(S - a)])
        rr = np.array([rhoR[t, a + t] for t in range(S - a)])
        cj = np.array([fe.cev((diag(cB, a, j), diag(nB, a, j)),
                              (diag(cR, a, j), diag(nR, a, j)), chi, rb, rr, j) for j in range(J)])
        ok = np.isfinite(cj) & (np.abs(cj) <= max_cev)
        if lam[ok].sum() < 0.5:                      # need most of the population to be reliable
            continue
        w = lam[ok] / lam[ok].sum()
        ages.append(E + a)
        cev_w.append(float(np.sum(w * cj[ok])) * 100)
        cev_lo.append(float(np.min(cj[ok])) * 100)
        cev_hi.append(float(np.max(cj[ok])) * 100)
    if not ages:
        return []
    ages = np.array(ages)

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.095, right=0.92)
    style.clean(ax, left=True)
    style.zero_line(ax)
    col = style.LOSS if np.nanmean(cev_w) < 0 else style.GAIN  # sign-honest, not assumed-loss
    ax.fill_between(ages, cev_lo, cev_hi, color=col, alpha=0.10, zorder=1,
                    label="income-group range")
    ax.plot(ages, cev_w, color=col, lw=2.4, zorder=3)
    style.label_ends(ax, [(ages[-1], cev_w[-1], "population avg", col)])
    _retire = style.retire_age(base_params)
    if _retire is not None:
        ax.axvline(_retire, color=style.SUB, lw=0.9, ls=(0, (4, 3)), zorder=2)
        ax.annotate("retirement", (_retire, ax.get_ylim()[0]), xytext=(5, 6),
                    textcoords="offset points", fontsize=8.5, color=style.SUB)
    ax.set_xlim(ages[0] - 1, ages[-1] + (ages[-1] - ages[0]) * 0.16)
    ax.set_xlabel("age at the reform")
    ax.set_ylabel("remaining-lifetime CEV (%)")
    ax.legend(loc="best", frameon=False, fontsize=8.5)  # auto-place to avoid the retirement marker
    style.title_block(
        fig, title="Lifetime welfare effect, by current age",
        subtitle=f"Welfare effect by age at the reform, averaged across income groups  ·  ages {ages[0]}–{ages[-1]}",
        source=style.source_line(note, extra=_BEQ_NOTE),
        kicker="welfare: CEV by age", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# ============================== DISTRIBUTION ==============================

STEP_COLORS = style.CATEGORICAL


STEP_LS = ["-", (0, (5, 2)), (0, (1, 1.4)), (0, (4, 2, 1, 2))]


def _lam_weighted_avg(dev, lam):
    """λ-weighted average of ``dev`` (S, J) across income groups, per age. Renormalizes the
    weights over the FINITE entries at each age, so groups masked to NaN (e.g. an undefined
    %-change) drop out of the average instead of silently biasing it toward 0 (mirrors
    cev_by_age's w = lam[ok]/lam[ok].sum() pattern, vectorized over ages)."""
    dev = np.asarray(dev, float)
    lam = np.asarray(lam, float).ravel()
    ok = np.isfinite(dev)                                     # (S, J)
    w = np.where(ok, lam[None, :], 0.0)                       # zero out missing groups' weight
    wsum = w.sum(axis=1)                                      # (S,)
    num = np.nansum(np.where(ok, dev, 0.0) * w, axis=1)       # (S,)
    return np.where(wsum > 0, num / np.where(wsum == 0, np.nan, wsum), np.nan)


def _lifecycle_band(ax, ages, dev, lam, base_params, *, band_label="income-group range",
                    line_label="population avg", color=None, right_pad=0.16, min_halfrange=None):
    """Shared lifecycle band builder for consumption_by_age and asset_by_age: a λ-weighted
    average line over the income-group fill_between(lo, hi) band, sign-colored (unless ``color``
    is forced), with the retirement marker and an end-of-line label. ``min_halfrange`` floors the
    y-axis half-range (e.g. 1.0%) so a near-null effect frames as small instead of being magnified
    into a dramatic wiggle. Returns (avg, color)."""
    avg = _lam_weighted_avg(dev, lam)
    lo, hi = np.nanmin(dev, axis=1), np.nanmax(dev, axis=1)
    c = color if color is not None else (style.LOSS if np.nanmean(avg) < 0 else style.GAIN)
    style.zero_line(ax)
    ax.fill_between(ages, lo, hi, color=c, alpha=0.10, zorder=1, label=band_label)
    ax.plot(ages, avg, color=c, lw=2.4, zorder=3)
    if min_halfrange is not None:                        # frame a near-null effect honestly (not magnified)
        ylo, yhi = ax.get_ylim()
        mid = 0.5 * (ylo + yhi)
        if 0.5 * (yhi - ylo) < min_halfrange:
            ax.set_ylim(mid - min_halfrange, mid + min_halfrange)
    style.label_ends(ax, [(ages[-1], avg[-1], line_label, c)])
    style.mark_retirement(ax, base_params, label_top=True)
    ax.set_xlim(ages[0] - 1, ages[-1] + (ages[-1] - ages[0]) * right_pad)
    return avg, c


def energy_demand_by_group(layered, out_dir, *, note=None, name="energy_by_income"):
    """Energy-good demand %-change by lifetime-income group, one line per channel step."""
    solved = [r for r in layered if "macro" in r and "energy_by_J" in r]
    if not solved:
        return []
    J = len(solved[0]["energy_by_J"])
    lab = _labels(J)
    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.17, left=0.085, right=0.80)
    style.clean(ax)
    ends = []
    for i, r in enumerate(solved):
        ev = np.asarray(r["energy_by_J"], float)
        c = STEP_COLORS[i % len(STEP_COLORS)]
        ls = STEP_LS[i % len(STEP_LS)]
        ax.plot(range(J), ev, marker="o", color=c, lw=2.0, ls=ls, zorder=2,
                markeredgecolor="white", markeredgewidth=0.8)
        ends.append((J - 1, ev[-1], r["step"], c))
    # Floor the collision gap: scaling off the smallest end alone collapses toward 0 when the
    # lowest line ends near 0, so fall back to a fraction of the spread of all ends.
    end_ys = [e[1] for e in ends]
    min_gap = max(0.05 * abs(min(end_ys)), 0.03 * (np.ptp(end_ys) or 1.0))
    style.label_ends(ax, ends, min_gap=min_gap)
    ax.set_xticks(range(J))
    ax.set_xticklabels(lab, rotation=30, ha="right")
    ax.set_xlim(-0.2, J - 1 + 0.5)
    ax.set_ylabel("energy-good demand change (%)")
    style.title_block(
        fig, title="Change in energy use, by income group",
        subtitle="Energy-good demand change by income group, poorest to richest  ·  one line per scenario",
        source=style.source_line(note), kicker="distribution: energy demand", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def consumption_by_age(base_ss, reform_ss, base_params, out_dir, *, note=None, max_age=90,
                       name="consumption_by_age"):
    """SS composite-consumption %-change by age: the λ-weighted lifecycle path with the income-
    group range as a band, showing when in life the deviation lands.
    Capped at ``max_age`` -- the final model ages are a terminal-period boundary (assets fully
    drawn down), not a lifecycle feature."""
    cb, cr = np.asarray(base_ss["c"], float), np.asarray(reform_ss["c"], float)  # (S, J)
    if cb.shape != cr.shape:
        return []
    E = int(base_params.E)
    lam = np.asarray(base_params.lambdas, float).ravel()
    dev = style.pct_dev(cr, cb)                                                  # (S, J)
    ages = E + np.arange(cb.shape[0])
    keep = ages <= int(max_age)
    ages, dev = ages[keep], dev[keep]

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.095, right=0.92)
    style.clean(ax, left=True)
    avg, _ = _lifecycle_band(ax, ages, dev, lam, base_params, color=style.LOSS, right_pad=0.16)
    ax.set_xlabel("age")
    ax.set_ylabel("consumption change vs baseline (%)")
    ax.legend(loc="lower left", frameon=False, fontsize=8.5)
    style.title_block(
        fig, title="Household spending change, by age",
        subtitle=f"Long-run change in spending over the life cycle, averaged across income groups "
                 f"(mean {np.nanmean(avg):+.2f}%)  ·  shaded band = range across income groups",
        source=style.source_line(note), kicker="distribution: by age", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def asset_by_age(base_ss, reform_ss, base_params, out_dir, *, note=None, max_age=85,
                 name="asset_by_age"):
    """SS household-asset %-change by age: the λ-weighted lifecycle path with the income-group
    range as a band -- the stock-side companion to consumption_by_age.
    Capped at ``max_age`` -- the final model ages are a terminal-period drawdown boundary (assets
    falling to ~0), not a lifecycle feature; the cap is tighter here than for consumption so the
    band/line do not plunge into that boundary at the right edge. Ages where baseline assets are
    ~0 are dropped from the %-change (the ratio is undefined there) rather than spiking."""
    if "b_s" not in base_ss or "b_s" not in reform_ss:
        return []
    bb, br = np.asarray(base_ss["b_s"], float), np.asarray(reform_ss["b_s"], float)  # (S, J)
    if bb.shape != br.shape or bb.ndim != 2:
        return []
    E = int(np.atleast_1d(base_params.E).flat[0])
    lam = np.asarray(base_params.lambdas, float).ravel()
    dev = style.pct_dev(br, bb)                                                   # (S, J)
    ages = E + np.arange(bb.shape[0])
    keep = ages <= int(max_age)
    ages, dev = ages[keep], dev[keep]

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.13, left=0.095, right=0.92)
    style.clean(ax, left=True)
    avg, _ = _lifecycle_band(ax, ages, dev, lam, base_params, right_pad=0.08, min_halfrange=1.0)
    ax.set_xlabel("age")
    ax.set_ylabel("asset change vs baseline (%)")
    ax.legend(loc="lower left", frameon=False, fontsize=8.5)
    style.title_block(
        fig, title="Household savings change, by age",
        subtitle=f"Long-run change in savings over the life cycle, averaged across income groups "
                 f"(mean {np.nanmean(avg):+.2f}%)  ·  shaded band = range across income groups",
        source=style.source_line(note), kicker="distribution: savings by age", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def income_composition_by_age(base_tpi, reform_tpi, base_params, out_dir, *, note=None,
                              max_age=80, name="income_composition_by_age"):
    """Near-term (t=0) %-deviation of the three household-income components -- labor income,
    capital income and bequests -- by age, λ-weighted over income groups, one line each.
    A transition snapshot: these are TPI-only quantities (no SS analogue), read at the first
    transition period. Components absent from the run are skipped; returns [] if none present.
    Capped at ``max_age`` -- the final model ages are a terminal-period boundary (assets fully
    drawn down), not a lifecycle feature -- so those spikes do not set the scale."""
    comps = [("labor_income", "labor income"), ("capital_income", "capital income"),
             ("bq", "income from inheritances")]
    lam = np.asarray(base_params.lambdas, float).ravel()
    E = int(np.atleast_1d(base_params.E).flat[0])
    series, ages = [], None
    for i, (key, lab) in enumerate(comps):
        if key not in base_tpi or key not in reform_tpi:
            continue
        arr_b, arr_r = np.asarray(base_tpi[key], float), np.asarray(reform_tpi[key], float)
        nyr = min(10, arr_b.shape[0])                    # first-decade average (period 0 is pre-phase-in)
        b0, r0 = arr_b[:nyr].mean(axis=0), arr_r[:nyr].mean(axis=0)               # (S, J)
        if b0.shape != r0.shape or b0.ndim != 2:
            continue
        a = E + np.arange(b0.shape[0])
        keep = a <= int(max_age)
        # Mask NEAR-zero baselines, not just exact zeros: e.g. labor income ~0 after retirement
        # makes the %-change ratio explode into a spurious terminal spike. Treat |base| below a
        # small fraction of the component's own peak as undefined (NaN) so it never sets the scale.
        tiny = 1e-3 * (np.nanmax(np.abs(b0)) or 1.0)
        # NaN the near-zero baselines first (not just exact zeros), then take the standard
        # %-deviation: style.pct_dev already maps an exact-zero base to NaN, so masking the
        # tiny entries to NaN here carries that same "undefined ratio" treatment through.
        b0m = np.where(np.abs(b0) < tiny, np.nan, b0)
        dev = style.pct_dev(r0, b0m)                                             # (S, J)
        dev = dev[keep]
        avg = _lam_weighted_avg(dev, lam)
        ages = a[keep] if ages is None else ages
        series.append((lab, avg, style.CATEGORICAL[i % len(style.CATEGORICAL)]))
    if not series:
        return []

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.4, 5.1))
    fig.subplots_adjust(top=0.76, bottom=0.18, left=0.095, right=0.84)
    style.clean(ax, left=True)
    style.zero_line(ax)
    ends = []
    for lab, avg, c in series:
        ax.plot(ages, avg, color=c, lw=2.2, zorder=3)
        ends.append((ages[-1], avg[-1], lab, c))
    finite = np.concatenate([np.asarray(a, float)[np.isfinite(a)] for _, a, _ in series])
    span = np.ptp(finite) or 1.0
    gap = 0.07 * span
    # Keep end-labels off the zero reference line: nudge any anchor sitting within the
    # min-gap band of zero out to its own side, so the axhline never strikes through text.
    off = 0.5 * gap
    ends = [(x, (off if y >= 0 else -off) if abs(y) < off else y, t, c)
            for (x, y, t, c) in ends]
    style.label_ends(ax, ends, min_gap=gap)
    style.mark_retirement(ax, base_params, label_top=True)
    ax.set_xlim(ages[0] - 1, ages[-1] + (ages[-1] - ages[0]) * 0.18)
    ax.set_xlabel("age")
    ax.set_ylabel("change in income vs baseline (%)")
    fig.text(0.045, 0.05,
             "Note: inheritances are split equally across households in this run, so the line is flat by design;\n"
             "it dips because fewer deaths leave fewer estates to pass on.",
             fontsize=8.5, color=style.SUB, ha="left", va="bottom")
    style.title_block(
        fig, title="Change in income, by source and age",
        subtitle="Labor income, capital income, and income from inheritances  ·  first-decade average, "
                 "across income groups",
        source=style.source_line(note),
        kicker="distribution: income sources", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# ============================== COMPOSITION ==============================

def _energy_index(attr, n, concordance=None):
    """Resolve an energy port (`attr` in {energy_good_index, energy_industry_index}) to a 0-based
    array index in range [0, n). The concordance value is already a 0-based position (see module
    note).

    The `concordance` is the PER-RUN one the viz driver loads from the run's baseline_meta.json (what
    the OG runner discovered). Returns None when it is absent or its port is unset/out of range, so
    callers degrade to no energy marker rather than guessing one (a country with no isolated energy
    industry/good simply has no asterisk)."""
    if concordance is None:
        return None
    try:
        idx0 = getattr(concordance, attr, None)
        idx0 = int(idx0) if idx0 is not None else None
    except (TypeError, ValueError):  # a garbled/partial concordance -> no marker
        return None
    return idx0 if idx0 is not None and 0 <= idx0 < n else None


def _good_labels(I, energy0=None, names=None):
    """Labels for the I composite consumption goods; the energy good (0-based `energy0`) gets a trailing
    asterisk. Uses the real good NAMES (CONS_DICT groups, recorded in baseline_meta) when they line up
    with I; otherwise falls back to 1-based "good k" -- so any model labels sensibly."""
    base = list(names) if (names and len(names) == I) else [f"good {k + 1}" for k in range(I)]
    return [base[k] + (" *" if energy0 is not None and k == energy0 else "") for k in range(I)]


def _sector_labels(M, energy0=None, names=None):
    """Labels for the M industries; the energy industry (0-based `energy0`) gets a trailing asterisk.
    Uses the real industry NAMES (PROD_DICT groups, recorded in baseline_meta) when they line up with M;
    otherwise falls back to 1-based "sector k"."""
    base = list(names) if (names and len(names) == M) else [f"sector {k + 1}" for k in range(M)]
    return [base[k] + (" *" if energy0 is not None and k == energy0 else "") for k in range(M)]


def consumption_by_good(base_ss, reform_ss, base_params, out_dir, *, note=None,
                        concordance=None, good_names=None, name="consumption_by_good"):
    """Steady-state %-change of each composite consumption good (C_i reform vs base), bars from
    zero, sign-colored, the computed % stamped on every bar. The energy good (concordance route A)
    is marked with an asterisk so the basket re-mix reads against its energy port -- by index, so
    it is portable across country models. `concordance` (the driver loads the per-run one from the run's
    baseline_meta.json) pins the energy port; None -> no asterisk."""
    cb_raw, cr_raw = base_ss.get("C_i"), reform_ss.get("C_i")
    cb = np.asarray(cb_raw, float).ravel() if cb_raw is not None else None
    cr = np.asarray(cr_raw, float).ravel() if cr_raw is not None else None
    if cb is None or cr is None or cb.shape != cr.shape or cb.size == 0:
        return []
    I = cb.size
    dev = style.pct_dev(cr, cb)
    energy0 = _energy_index("energy_good_index", I, concordance)
    lab = _good_labels(I, energy0, good_names)

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    fig.subplots_adjust(top=0.76, bottom=0.17, left=0.10, right=0.95)
    style.clean(ax)
    style.zero_line(ax)
    ax.bar(range(I), dev, width=0.66, color=style.signed(dev), zorder=2)
    for k, v in enumerate(dev):
        if not np.isfinite(v):
            continue
        ax.annotate(f"{v:+.2f}%", (k, v), xytext=(0, -11 if v < 0 else 6),
                    textcoords="offset points", ha="center", va="top" if v < 0 else "bottom",
                    fontsize=9, fontweight="bold", color=style.LOSS if v < 0 else style.GAIN)
    ax.set_xticks(range(I))
    ax.set_xticklabels(lab)
    ax.margins(y=0.20)
    ax.set_ylabel("consumption change vs baseline (%)")
    fin = dev[np.isfinite(dev)]
    if energy0 is not None and good_names and len(good_names) == I:
        parts = [f"goods are composite categories; * marks the energy good ({good_names[energy0]})"]
    elif energy0 is not None:
        parts = [(f"goods are composite categories; * marks the energy good (good {energy0 + 1}), "
                 f"the only one identified")]
    else:
        parts = ["goods are composite categories"]
    if fin.size:
        parts.append(f"range {np.min(fin):+.2f}% to {np.max(fin):+.2f}%")
    sub = "  ·  ".join(parts)
    style.title_block(
        fig, title="Long-run change in spending, by type of good",
        subtitle=sub, source=style.source_line(note),
        kicker="composition: by good", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def sectoral_reallocation(base_ss, reform_ss, base_params, out_dir, *, note=None,
                          concordance=None, industry_names=None, name="sectoral_reallocation"):
    """Steady-state %-change by industry of output (Y_m), capital (K_m), and labor (L_m) -- a
    three-series dot plot, one cluster per sector, the computed values labeled. The energy industry
    (concordance route B) is marked with an asterisk. Dots (position/length encodings) keep the
    three series legible on one honest, zero-anchored scale. `concordance` (the driver loads the per-run
    one from the run's baseline_meta.json) pins the energy port; None -> no asterisk."""
    series = []
    for key, lbl, col in (("Y_m", "output", style.CATEGORICAL[0]),
                          ("K_m", "capital", style.CATEGORICAL[2]),
                          ("L_m", "labor", style.CATEGORICAL[3])):
        b, r = base_ss.get(key), reform_ss.get(key)
        if b is None or r is None:
            continue
        b = np.asarray(b, float).ravel()
        r = np.asarray(r, float).ravel()
        if b.shape != r.shape or b.size == 0:
            continue
        series.append((lbl, col, style.pct_dev(r, b)))
    if not series:
        return []
    M = series[0][2].size
    if any(s[2].size != M for s in series):
        return []
    energy0 = _energy_index("energy_industry_index", M, concordance)
    lab = _sector_labels(M, energy0, industry_names)

    os.makedirs(out_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    fig.subplots_adjust(top=0.74, bottom=0.12, left=0.16, right=0.86)
    style.clean(ax, left=False, grid="x")          # horizontal dot plot: vertical (x) gridlines
    style.zero_line(ax, axis="x")
    n = len(series)
    spread = 0.26                                  # vertical offset of the three markers per sector
    offs = np.linspace(-spread, spread, n) if n > 1 else np.array([0.0])
    markers = ["o", "s", "D", "^", "v"]
    all_vals = np.concatenate([s[2][np.isfinite(s[2])] for s in series]) if series else np.array([])
    span = (np.max(all_vals) - np.min(all_vals)) if all_vals.size else 1.0
    for si, (lbl, col, vals) in enumerate(series):
        ys = np.arange(M) + offs[si]
        ax.scatter(vals, ys, s=64, color=col, marker=markers[si % len(markers)], zorder=3,
                   label=lbl, edgecolor="white", linewidth=0.6)
        for k, v in enumerate(vals):
            if not np.isfinite(v):
                continue
            ax.annotate(f"{v:+.2f}%", (v, ys[k]),
                        xytext=(6 if v >= 0 else -6, 0), textcoords="offset points",
                        ha="left" if v >= 0 else "right", va="center",
                        fontsize=7.5, color=col)
    ax.set_yticks(range(M))
    ax.set_yticklabels(lab)
    ax.invert_yaxis()                              # sector 1 at top, reading order
    ax.set_ylim(M - 0.5, -0.5)
    if all_vals.size:
        lo, hi = np.min(all_vals), np.max(all_vals)
        ax.set_xlim(lo - 0.16 * (span or 1.0), hi + 0.20 * (span or 1.0))
    ax.set_xlabel("change vs baseline (%)")
    ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    _named = bool(industry_names and len(industry_names) == M)
    sub = ("model sectors are composite industries" if _named
           else "model sectors are composite industries; only the energy industry is identified")
    if energy0 is not None:
        _en = industry_names[energy0] if _named else f"sector {energy0 + 1}"
        sub += f"  ·  * marks the energy industry ({_en})"
    else:
        sub += "  ·  output, capital, and jobs, one cluster per industry"
    style.title_block(
        fig, title="Long-run change by industry: output, capital, jobs",
        subtitle=sub, source=style.source_line(note),
        kicker="composition: by sector", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def consumption_by_good_by_group(base_tpi, reform_tpi, base_params, out_dir, *, note=None,
                                 concordance=None, good_names=None, name="consumption_by_good_by_group"):
    """Near-term (t=0) consumption-quantity %-change by good for a few lifetime-income groups
    (poorest / middle / richest), as small multiples -- one panel per group, a bar per good. The
    quantity is c_i (T,I,S,J) at t=0 aggregated over ages -> (I,J), so the bars compare WHAT each
    group buys more/less of. The energy good (concordance route A) is marked with an asterisk."""
    cib = base_tpi.get("c_i")
    cir = reform_tpi.get("c_i")
    if cib is None or cir is None:
        return []
    cib = np.asarray(cib, float)
    cir = np.asarray(cir, float)
    if cib.shape != cir.shape or cib.ndim != 4 or cib.shape[0] == 0:
        return []
    # t=0, aggregate over ages (axis=S) -> (I, J) consumption-quantity per good per group
    b0 = cib[0].sum(axis=1)
    r0 = cir[0].sum(axis=1)
    I, J = b0.shape
    dev = style.pct_dev(r0, b0)                      # (I, J)

    # poorest / middle / richest -- distinct indices, degrade if J is tiny
    picks = sorted({0, J // 2, J - 1})
    if not picks:
        return []
    lam = None
    try:
        lam = np.asarray(base_params.lambdas, float).ravel()
        if lam.size != J:
            lam = None
    except Exception:  # noqa: BLE001
        lam = None
    glab = _labels(J, lam)
    energy0 = _energy_index("energy_good_index", I, concordance)
    xlab = _good_labels(I, energy0, good_names)

    finite = dev[:, picks][np.isfinite(dev[:, picks])]
    vmax = np.max(np.abs(finite)) if finite.size else 1.0
    ylim = vmax * 1.30 or 1.0

    os.makedirs(out_dir, exist_ok=True)
    n = len(picks)
    fig, axes = plt.subplots(1, n, figsize=(3.1 * n + 1.4, 5.0), sharey=True)
    axes = np.atleast_1d(axes)
    fig.subplots_adjust(top=0.74, bottom=0.20, left=0.085, right=0.97, wspace=0.18)
    for ai, j in enumerate(picks):
        ax = axes[ai]
        vals = dev[:, j]
        style.clean(ax, left=(ai == 0))
        style.zero_line(ax)
        ax.bar(range(I), vals, width=0.70, color=style.signed(vals), zorder=2)
        for k, v in enumerate(vals):
            if not np.isfinite(v):
                continue
            ax.annotate(f"{v:+.1f}%", (k, v), xytext=(0, -9 if v < 0 else 5),
                        textcoords="offset points", ha="center",
                        va="top" if v < 0 else "bottom", fontsize=7.0,
                        color=style.LOSS if v < 0 else style.GAIN)
        ax.set_xticks(range(I))
        ax.set_xticklabels(xlab, rotation=30, ha="right", fontsize=8)
        ax.set_ylim(-ylim, ylim)
        ax.set_title(glab[j] if j < len(glab) else f"group {j + 1}")
        if ai == 0:
            ax.set_ylabel("consumption change vs baseline (%)")
    sub = "Year-0 change in spending by type of good, for the poorest / middle / richest group"
    if energy0 is not None and good_names and len(good_names) == I:
        sub += f"  ·  goods are composite categories; * marks the energy good ({good_names[energy0]})"
    elif energy0 is not None:
        sub += (f"  ·  goods are composite categories; * marks the energy good (good {energy0 + 1}), "
                f"the only one identified")
    else:
        sub += "  ·  goods are composite categories"
    style.title_block(
        fig, title="Change in spending by type of good, across income groups",
        subtitle=sub, source=style.source_line(note),
        kicker="composition: good x group", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


# ============================== DASHBOARD ==============================

def _panel_emissions(ax, country, illustrative=True):
    from oglink import signals
    eb = signals.emissions_by_year(country.scenario.base_dir, country)
    er = signals.emissions_by_year(country.scenario.reform_dir, country)
    erb = eb.reindex(er.index)
    ax.plot(eb.index, eb.values, color=style.MUTE, lw=2.0, zorder=2)
    ax.plot(er.index, er.values, color=style.GAIN, lw=2.2, zorder=3)
    ax.fill_between(er.index, erb.values, er.values, color=style.GAIN, alpha=0.12, zorder=1)
    style.label_ends(ax, [(eb.index[-1], eb.values[-1], "base", style.MUTE),
                          (er.index[-1], er.values[-1], "reform", style.GAIN)], min_gap=0.0)
    # the headline number: cumulative avoided emissions (worth showing, as in earlier versions)
    avoided = float(np.nansum(erb.values - er.values))
    if np.isfinite(avoided) and abs(avoided) > 0:
        units = " (model units)" if illustrative else ""
        word = "avoided" if avoided > 0 else "added"
        ax.annotate(f"cumulative {word} ≈ {abs(avoided):,.0f} {country.co2_emission}{units}",
                    (0.03, 0.95), xycoords="axes fraction", ha="left", va="top",
                    fontsize=8.5, color=style.TEAL, fontweight="medium")
    yr0, yr1 = int(eb.index[0]), int(er.index[-1])
    ax.set_xlim(right=float(er.index[-1]) + (float(er.index[-1]) - float(er.index[0])) * 0.18)
    ax.set_ylabel(f"emissions ({country.co2_emission})")
    ax.set_title(f"1 · Emissions: baseline vs reform ({yr0}-{yr1})")


def _panel_macro(ax, base_tpi, reform_tpi, start_year, params=None, n_years=80):
    # Clamp to the closure window and mark where the budget rule begins -- same as the standalone
    # macro figure. We don't plot the long forced-closure glide (it's not the interesting part).
    closure_year, hz = _closure_window(params, start_year, n_years)
    n = _clamp_n(hz, base_tpi, reform_tpi, "Y", "C")
    yrs = _years(start_year, n)
    for v, lab, c in (("Y", "GDP", style.CATEGORICAL[0]), ("C", "consumption", style.CATEGORICAL[1])):
        d = _pct_path(base_tpi, reform_tpi, v, n)
        ax.plot(yrs, d, color=c, lw=2.2, zorder=2)
        ax.annotate(lab, (yrs[-1], d[-1]), xytext=(5, 0), textcoords="offset points",
                    color=c, fontsize=9.5, fontweight="medium", va="center")
    style.zero_line(ax)
    ax.set_xlim(yrs[0], yrs[-1] + (yrs[-1] - yrs[0]) * 0.18)
    _closure_line(ax, closure_year, yrs)
    ax.set_ylabel("change vs baseline (%)")
    ax.set_title(f"2 · The economy over time ({yrs[0]}-{yrs[-1]})")


def _panel_waterfall(ax, layered):
    solved = [r for r in layered if "macro" in r]
    if len(solved) < 2:  # single scenario: no bridge to span -> show ITS macro impact bars instead
        m = (solved[0].get("macro") if solved else {}) or {}
        keys = [("Y", "GDP"), ("C", "consumption"), ("K", "capital"), ("L", "labor")]
        vals = [m.get(k) for k, _ in keys]
        fin = [float(v) for v in vals if v is not None]
        style.zero_line(ax)
        ax.bar(range(len(vals)), [float(v) if v is not None else 0.0 for v in vals],
               color=style.signed([float(v) if v is not None else 0.0 for v in vals]), width=0.6, zorder=2)
        for i, v in enumerate(vals):
            if v is not None:
                ax.annotate(style.signed_pct(v, fin), (i, v), xytext=(0, -11 if v < 0 else 6),
                            textcoords="offset points", ha="center", va="top" if v < 0 else "bottom",
                            fontsize=9, fontweight="bold", color=style.LOSS if v < 0 else style.GAIN)
        ax.set_xticks(range(len(keys)))
        ax.set_xticklabels([lab for _, lab in keys])
        ax.margins(y=0.22)
        ax.set_ylabel("change vs baseline (%)")
        ax.set_title("3 · Macro impact of the coupled scenario  ·  first 10 years")
        return
    labels = [r["step"].replace("+ ", "") for r in solved]
    yvals = [r["macro"]["Y"] for r in solved]
    marg, cum = _bridge(yvals)
    for i, m in enumerate(marg):
        ax.bar(i, m, bottom=cum[i], color=style.GAIN if m >= 0 else style.LOSS, width=0.64, zorder=2)
        if i < len(marg) - 1:
            ax.plot([i + 0.32, i + 1 - 0.32], [cum[i + 1], cum[i + 1]], color="0.6", lw=0.8, zorder=1)
    style.zero_line(ax)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.margins(y=0.22)
    ax.set_ylabel("GDP change vs baseline (%)")
    ax.text(0.03, 0.96, f"net {cum[-1]:+.3f}%", transform=ax.transAxes, fontsize=9.5,
            fontweight="bold", color=style.INK, va="top", ha="left")  # net IN the panel, not the title
    ax.set_title("3 · Each scenario's contribution to GDP  ·  first 10 years")


def _panel_cev(ax, base_ss, reform_ss, base_params, reform_params):
    fe = _Felicity(base_params)
    cb, nb = np.asarray(base_ss["c"], float), np.asarray(base_ss["n"], float)
    cr, nr = np.asarray(reform_ss["c"], float), np.asarray(reform_ss["n"], float)
    chi = np.asarray(base_params.chi_n, float)[-1]
    rho_b, rho_r = np.asarray(base_params.rho, float)[-1], np.asarray(reform_params.rho, float)[-1]
    J = cb.shape[1]
    cev = 100.0 * np.array([fe.cev((cb[:, j], nb[:, j]), (cr[:, j], nr[:, j]), chi, rho_b, rho_r, j)
                            for j in range(J)])
    ax.bar(range(J), cev, width=0.66, color=style.signed(cev), zorder=2)
    style.zero_line(ax)
    ax.set_xticks(range(J))
    ax.set_xticklabels(_labels(J), rotation=30, ha="right", fontsize=8)
    ax.margins(y=0.18)
    ax.set_ylabel("lifetime welfare change vs baseline (%)")
    ax.set_title("4 · Welfare change from baseline, by income group  ·  long-run")


def headline_dashboard(layered, base_tpi, reform_tpi, base_ss, reform_ss, base_params,
                       reform_params, country, out_dir, *, start_year, note=None,
                       illustrative=True, name="headline_dashboard"):
    """The whole coupled run on one slide: emissions, macro dynamics, channel decomposition, welfare."""
    os.makedirs(out_dir, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(12.6, 9.4))
    fig.subplots_adjust(top=0.80, bottom=0.085, left=0.075, right=0.965, hspace=0.42, wspace=0.22)
    for ax in axes.ravel():
        style.clean(ax, left=True)

    try:
        _panel_emissions(axes[0, 0], country, illustrative=illustrative)
    except Exception:  # noqa: BLE001 -- emissions needs the external CLEWS dir; degrade gracefully + LOUDLY
        print("  (dashboard panel 1: emissions path unavailable -- CLEWS scenario files not found)")
        axes[0, 0].set_title("1 · Emissions: baseline vs reform")
        axes[0, 0].text(0.5, 0.5, "Emissions path not available\n(needs the CLEWS scenario files)",
                        ha="center", va="center", transform=axes[0, 0].transAxes,
                        color=style.MUTE, fontsize=9.5)
    _panel_macro(axes[0, 1], base_tpi, reform_tpi, start_year, base_params)
    _panel_waterfall(axes[1, 0], layered)
    _panel_cev(axes[1, 1], base_ss, reform_ss, base_params, reform_params)

    # No deck-level subtitle: each panel titles itself, and a subtitle here reads as if it
    # describes only panel 1.
    style.title_block(
        fig, title=f"{country.name}: coupled OG-Core × CLEWS scenario",
        source=style.source_line(note), kicker="headline dashboard", top=0.975)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]
