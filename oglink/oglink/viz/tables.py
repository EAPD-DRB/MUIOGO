"""The deck's table-as-figure pages: the cover, the across-steps summary table, and the CSV the
table mirrors -- the output_tables analog to plots.py. Pure chrome built on the house theme; reads
numbers straight from the layered records, never recomputes a finding."""
from __future__ import annotations

import csv
import os
import textwrap

import matplotlib

matplotlib.use("Agg")

from . import style

style.apply()
import matplotlib.pyplot as plt


def _solved(layered):
    """The records that carry a solved macro block, in run order (degrade to [] if none)."""
    return [r for r in (layered or []) if isinstance(r, dict) and "macro" in r]


def _fmt_pct(v):
    """Signed percent with a fixed 2 decimals; '--' when the field is absent. Normalizes
    -0.0 to 0.0 so a rounded-to-zero value never prints a spurious minus sign."""
    if v is None:
        return "--"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "--"
    if f == 0.0:
        f = 0.0
    return f"{f:+.2f}"


def _text_page(out_dir, name, *, draw, figsize=(8.4, 10.9)):
    """A full-figure text page for figure-coord text. The draw callback writes via fig.text only
    (no axis is used), so we add none -- that lets savefig.bbox='tight' crop the canvas to the
    text block instead of leaving a large empty band of unused page. Returns the saved path in a
    one-element list (the builder contract)."""
    os.makedirs(out_dir, exist_ok=True)
    fig = plt.figure(figsize=figsize)
    draw(fig, None)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def _marginal(cur, prev):
    """Marginal contribution of a step: the column-wise change from the previous step's cumulative
    values (the first step's previous is baseline = 0). None where either side is absent."""
    return [None if c is None or p is None else c - p for c, p in zip(cur, prev)]


def summary_table(layered, out_dir, *, note=None, name="summary_table"):
    """The across-steps results as a table-as-figure: columns Y%, C%, K%, L%, energy demand %,
    cons-tax revenue % (same field selection as figures.across_steps_table's CSV). The stored
    step values are CUMULATIVE (each step layered on the last), so each printed row is the step's
    MARGINAL contribution (this step's cumulative minus the previous step's) and a final Total row
    restates the full-reform cumulative -- the marginals sum to it. Values are the average over the
    first 10 transition years (the run's macro_pct_diff window), not a steady-state level.
    Numeric cells use a single neutral ink; the +/- sign carries direction, color carries no
    good/bad meaning (so falling energy demand, the policy goal, never reads as "bad")."""
    solved = _solved(layered)
    if not solved:
        return []
    os.makedirs(out_dir, exist_ok=True)

    col_labels = ["scenario", "Output %", "Consumption %", "Capital %", "Labor %",
                  "Energy demand %", "Consumption-tax revenue %"]

    def _cumvals(r):
        macro = r.get("macro", {}) or {}
        fiscal = r.get("fiscal", {}) or {}
        return [macro.get("Y"), macro.get("C"), macro.get("K"), macro.get("L"),
                r.get("energy_demand_pct"), fiscal.get("cons_tax_revenue_pct")]

    single = len(solved) == 1  # one coupled scenario -> its marginal IS the total; no redundant row
    cum = [_cumvals(r) for r in solved]
    rows, prev = [], [0.0] * len(col_labels[1:])
    for r, cv in zip(solved, cum):
        rows.append([str(r.get("step", ""))] + [_fmt_pct(v) for v in _marginal(cv, prev)])
        prev = cv
    # Multi-scenario: a Total row restating the full-reform cumulative (== the marginal sum). For a
    # single scenario that row would just duplicate the one data row, so it is omitted.
    total_idx = (len(rows) + 1) if not single else -1  # +1 for the header; -1 = no Total row present
    if not single:
        rows.append(["All scenarios (total)"] + [_fmt_pct(v) for v in cum[-1]])

    # Height floor so the title block (kicker + title + subtitle) always has room above the table --
    # a 1-2 row table would otherwise be too short and the subtitle would ride into the title.
    fig, ax = plt.subplots(figsize=(10.0, max(3.9, 1.4 + 0.62 * (len(rows) + 1))))
    fig.subplots_adjust(top=0.74, bottom=0.10, left=0.045, right=0.965)
    ax.set_axis_off()

    ncols = len(col_labels)
    # bbox=[0,0,1,1] makes the table fill its axes, so it sits directly under the subtitle with no
    # tall empty band from vertical centering. Column widths still size to content below.
    table = ax.table(cellText=rows, colLabels=col_labels, cellLoc="right", bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    # Size each column to its widest cell so the spelled-out headers (e.g. "Consumption-tax
    # revenue %") get the room they need instead of colliding with the neighbour.
    table.auto_set_column_width(col=list(range(ncols)))
    for (rr, cc), cell in table.get_celld().items():
        cell.set_edgecolor(style.GRID)
        cell.set_linewidth(0.7)
        if cc == 0:
            cell.set_text_props(ha="left")
            cell.PAD = 0.04
        if rr == 0:  # header row
            cell.set_text_props(color=style.INK, fontweight="bold")
            cell.set_facecolor("white")
            cell.visible_edges = "B"  # underline only
            cell.set_linewidth(1.0)
            cell.set_edgecolor("#333333")
            continue
        cell.visible_edges = "B"
        # Numeric body cells carry no good/bad color encoding -- the +/- sign in the text
        # already shows direction. A single neutral ink keeps falling energy demand (the
        # policy goal) from reading as "bad".
        cell.set_text_props(color=style.INK)
        if rr == total_idx:  # the Total row: bold, set off by a rule above
            cell.set_text_props(color=style.INK, fontweight="bold")
            cell.visible_edges = "T"
            cell.set_linewidth(1.0)
            cell.set_edgecolor("#333333")

    # subtle banding for row legibility (data-ink stays low: faint, behind text); skip the Total row
    for rr in range(1, len(rows) + 1):
        if rr % 2 == 0 and rr != total_idx:
            for cc in range(ncols):
                table[(rr, cc)].set_facecolor("#FAFAFA")

    if single:
        title = "Macro impact of the coupled scenario over the first 10 years"
        subtitle = "Average % change vs baseline over the first 10 transition years"
    else:
        title = "Contribution of each scenario over the first 10 years"
        subtitle = ("Average % change vs baseline  ·  each row is that scenario's own (marginal) "
                    "contribution; the last line is all scenarios combined")
    style.title_block(fig, title=title, subtitle=subtitle,
                      source=style.source_line(note), kicker="summary table", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def macro_table_figure(base_tpi, reform_tpi, start_year, out_dir, *, note=None, name="macro_table"):
    """The OG-Core-standard macro aggregates table as a figure: % change reform vs baseline for
    output, consumption, investment, capital and labour, plus the interest and wage rates -- year by
    year over the first decade, a 10-year-window average, and the steady state. Mirrors
    ``ogcore.output_tables.macro_table`` (the summary economists expect), built from `report.macro_table`.
    r and w are percentage-point rate differences. Works for any run (the variables present are shown)."""
    from oglink import report
    want = ("Y", "C", "I", "K", "L", "r", "w")
    df = report.macro_table(base_tpi, reform_tpi, start_year, var_list=want)
    if df is None or getattr(df, "empty", True):
        return []
    os.makedirs(out_dir, exist_ok=True)
    labels = {"Y": "Output %", "C": "Consumption %", "I": "Investment %", "K": "Capital %",
              "L": "Labour %", "r": "Interest rate (pp)", "w": "Wage (pp)"}
    col_labels = ["Year"] + [labels.get(c, c) for c in df.columns]
    idxs = [str(i) for i in df.index]
    rows = [[i] + [_fmt_pct(df.loc[df.index[k], c]) for c in df.columns] for k, i in enumerate(idxs)]
    # the window-average ("YYYY-YYYY") and steady-state ("SS") rows are summaries -> set them off
    setoff = {k for k, i in enumerate(idxs, start=1) if i == "SS" or "-" in i}

    ncols = len(col_labels)
    fig, ax = plt.subplots(figsize=(10.0, max(4.8, 1.7 + 0.34 * (len(rows) + 1))))
    fig.subplots_adjust(top=0.80, bottom=0.06, left=0.045, right=0.965)
    ax.set_axis_off()
    table = ax.table(cellText=rows, colLabels=col_labels, cellLoc="right", bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.auto_set_column_width(col=list(range(ncols)))
    for (rr, cc), cell in table.get_celld().items():
        cell.set_edgecolor(style.GRID)
        cell.set_linewidth(0.6)
        if cc == 0:
            cell.set_text_props(ha="left")
            cell.PAD = 0.03
        if rr == 0:  # header
            cell.set_text_props(color=style.INK, fontweight="bold")
            cell.set_facecolor("white")
            cell.visible_edges = "B"
            cell.set_linewidth(1.0)
            cell.set_edgecolor("#333333")
            continue
        cell.set_text_props(color=style.INK)  # neutral ink; the +/- sign carries direction (no red/green)
        cell.visible_edges = "B"
        if rr in setoff:  # window-avg + SS rows: bold, ruled off from the year-by-year block
            cell.set_text_props(fontweight="bold")
            cell.visible_edges = "T"
            cell.set_linewidth(1.0)
            cell.set_edgecolor("#333333")
    for rr in range(1, len(rows) + 1):  # faint banding on the year rows for legibility
        if rr % 2 == 0 and rr not in setoff:
            for cc in range(ncols):
                table[(rr, cc)].set_facecolor("#FAFAFA")

    style.title_block(
        fig, title="Macro aggregates over the transition",
        subtitle="% change vs baseline (interest rate and wage as percentage-point differences)  ·  "
                 "year by year, the first-decade average, then the steady state",
        source=style.source_line(note), kicker="macro table", top=0.965)
    return [style.save(fig, os.path.join(out_dir, f"{name}.png"))]


def cover_page(layered, country, fig_titles, out_dir, *, note=None, illustrative=True, name="cover"):
    """The deck's title page: country name + scenario headline, a plain-language statement of the
    scenario (the four changes described by MECHANISM, and what the health channel is), and a
    contents list of the section titles in `fig_titles`. Magnitudes are NOT asserted here -- they
    are scenario-specific and ride in the source note -- so the cover is honest and general across
    runs; `illustrative` only tags the deck as illustrative. States no result."""
    cname = getattr(country, "name", None) or "country"
    titles = [str(t) for t in (fig_titles or []) if str(t).strip()]
    tag = "  (illustrative magnitudes)" if illustrative else ""

    def draw(fig, ax):
        style.title_block(
            fig,
            title=f"{cname}: coupled OG-Core x CLEWS scenario",
            subtitle="An economy-wide model of households over their whole life, coupled to an"
                     " energy, land and water system.",
            kicker="scenario deck", top=0.965)

        x, y = 0.045, 0.80

        def para(text, *, bold=False, color=style.SUB, size=10.5, gap=0.012):
            nonlocal y
            for chunk in textwrap.wrap(text, 96) or [""]:
                fig.text(x, y, chunk, fontsize=size, color=color,
                         fontweight="bold" if bold else "normal", ha="left", va="top")
                y -= 0.031
            y -= gap

        # Plain-language statement of the scenario -- the changes described by MECHANISM. The actual
        # magnitudes ride in the source note (scenario-specific), so the cover is honest and general:
        # it never asserts a "+20%"/"$50" a given run may not use.
        para("The scenario", bold=True, size=11.5, color=style.INK)
        para(f"The coupled scenario changes the economy in four ways{tag}; "
             "this run's specific magnitudes are in the note below:")
        para("1.  Energy price -- a change in the price of the energy good, taken from the energy model.",
             color=style.INK)
        para("2.  Clean-energy investment -- the energy model's grid and generation capex, "
             "added to public investment.", color=style.INK)
        para("3.  Carbon tax -- a price on CO2 emissions, charged on the energy good.",
             color=style.INK)
        para("4.  Health -- cleaner air means fewer pollution deaths and less illness, so people "
             "live and work longer; derived from the emissions change.", color=style.INK)
        y -= 0.020

        if titles:
            fig.text(x, y, "Contents", fontsize=11.5, fontweight="bold", color=style.INK,
                     ha="left", va="top")
            y -= 0.040
            for i, t in enumerate(titles, 1):
                wrapped = textwrap.wrap(t, 84) or [""]
                fig.text(0.065, y, f"{i:>2}.", fontsize=10.0, color=style.MUTE,
                         ha="left", va="top")
                for k, chunk in enumerate(wrapped):
                    fig.text(0.105, y, chunk, fontsize=10.5,
                             color=style.INK if k == 0 else style.SUB, ha="left", va="top")
                    y -= 0.030
                y -= 0.006

        # Source rides just below the contents (not pinned to the page bottom) so the tight-crop
        # fits the cover to its content instead of leaving a tall empty band beneath it.
        fig.text(x, y - 0.03, style.source_line(note), fontsize=8, color=style.MUTE,
                 ha="left", va="top", wrap=True)

    return _text_page(out_dir, name, draw=draw)


def across_steps_table(layered, path):
    solved = [r for r in layered if "macro" in r]
    if not solved:
        return None
    # the energy-good columns (demand response + per-group consumption) are dropped when the run has no
    # isolated energy good (energy channels skipped); write the macro/fiscal-only table in that case.
    has_energy = all("consumption_by_J" in r for r in solved)
    lab = style.income_labels(len(solved[0]["consumption_by_J"])) if has_energy else []
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step"] + (["energy_demand_pct"] if has_energy else [])
                   + ["Y_pct", "C_pct", "K_pct", "L_pct", "govt_revenue_pct"]
                   + [f"consumption_{x}" for x in lab])
        for r in solved:
            w.writerow([r["step"]] + ([r["energy_demand_pct"]] if has_energy else [])
                       + [r["macro"].get(v) for v in ("Y", "C", "K", "L")]
                       + [r["fiscal"]["cons_tax_revenue_pct"]]
                       + (r["consumption_by_J"] if has_energy else []))
    return path
