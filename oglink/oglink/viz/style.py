"""Editorial house style for the coupled-run figures -- an FT / Economist / OWID-grade
matplotlib theme plus the layout helpers that separate a publication graphic from script
output. Grounded in a data-viz research pass (FT o-colors, Economist red, Okabe-Ito
colorblind-safe categorical, Datawrapper/Roboto, Wilke's "Fundamentals") and an adversarial
critique of the prior figures.

Use: `from . import style; style.apply()` then the helpers (title_block, clean, zero_line,
label_ends, save). The theme is idempotent; helpers take a matplotlib fig/ax.

Typography: stack prefers Source Sans 3 (the editorial target) and falls through to Roboto
(already present on macOS, Datawrapper's own default) -- so figures look right with no install,
and auto-upgrade if Source Sans 3 / Inter are dropped into ~/Library/Fonts.
"""
from __future__ import annotations

import itertools
import os
import platform
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm

# --- palette: editorial, colorblind-safe -----------------------------------------
INK, SUB, MUTE, GRID = "#222222", "#555555", "#888888", "#E6E6E6"
EDGE = "#333333"  # reference grey shared by the axes frame, the bottom spine, and the zero line
# diverging gains vs losses, centered on a neutral zero (RdBu poles: CB-safe, not traffic-light)
LOSS, GAIN, NEUTRAL = "#B2182B", "#2166AC", "#F7F7F7"
TOTAL = "#33302E"
# categorical: Okabe-Ito-derived + FT oxford / Economist red -- evenly spaced hues, CB-safe
CATEGORICAL = ["#0F5499", "#E3120B", "#0D7680", "#E69F00", "#7A6FAC", "#7F8C8D"]
# sequential blue ramp for ordered income groups (poorest -> richest)
SEQUENTIAL = ["#C6DBEF", "#9ECAE1", "#6BAED6", "#4292C6", "#2171B5", "#08519C", "#08306B"]
# kicker accent colors
CLARET, OXFORD, TEAL = "#990F3D", "#0F5499", "#0D7680"

_FONT_STACK = ["Source Sans 3", "Source Sans Pro", "Inter", "Roboto",
               "Helvetica Neue", "Arial", "DejaVu Sans"]


def _user_font_dirs():
    """Per-OS user font directories (MUIOGO convention: branch on ``platform.system()``). Windows fonts
    live under %LOCALAPPDATA% / %WINDIR%, macOS under ~/Library/Fonts, Linux under ~/.local/share/fonts."""
    sysname = platform.system()
    if sysname == "Windows":
        local, windir = os.environ.get("LOCALAPPDATA", ""), os.environ.get("WINDIR", "")
        dirs = []
        if local:
            dirs.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
        if windir:
            dirs.append(Path(windir) / "Fonts")
        return dirs
    if sysname == "Darwin":
        return [Path.home() / "Library" / "Fonts"]
    return [Path.home() / ".local" / "share" / "fonts", Path.home() / ".fonts"]   # Linux/other


def _register_local_fonts():
    """Make matplotlib see editorial fonts without rebuilding its global cache: user-installed (the
    per-OS user font dirs) and any bundled with the package (assets/fonts). Fonts are optional -- the
    _FONT_STACK falls back to DejaVu Sans -- so a dir that isn't there is simply skipped."""
    pats = ("SourceSans3-*.[ot]tf", "SourceSansPro-*.[ot]tf", "Inter-*.[ot]tf",
            "Inter*.[ot]tf", "IBMPlexSans-*.[ot]tf", "Roboto-*.ttf")
    paths = []
    for fdir in _user_font_dirs():
        if fdir.is_dir():
            for pat in pats:
                paths += fdir.glob(pat)
    bundled = Path(__file__).with_name("assets") / "fonts"
    if bundled.is_dir():
        paths += list(bundled.glob("*.ttf")) + list(bundled.glob("*.otf"))
    for f in paths:
        try:
            fm.fontManager.addfont(str(f))
        except Exception:  # noqa: BLE001 -- a bad font file must not break plotting
            pass


_applied = False


def apply():
    """Install the theme into matplotlib's rcParams (idempotent)."""
    global _applied
    if _applied:
        return
    _register_local_fonts()
    mpl.rcParams.update({
        # typography
        "font.family": "sans-serif", "font.sans-serif": _FONT_STACK, "font.size": 10.5,
        "text.color": INK,
        # titles / labels (we mostly drive titles via title_block; these are panel-label defaults)
        "axes.titlesize": 11, "axes.titleweight": "regular", "axes.titlecolor": SUB,
        "axes.titlelocation": "left", "axes.titlepad": 7,
        "axes.labelsize": 10.5, "axes.labelcolor": SUB,
        # ticks: no marks, gridlines carry the scale
        "xtick.labelsize": 9.5, "ytick.labelsize": 9.5,
        "xtick.color": SUB, "ytick.color": SUB, "xtick.labelcolor": SUB, "ytick.labelcolor": SUB,
        "xtick.major.size": 0, "ytick.major.size": 0, "xtick.major.pad": 5, "ytick.major.pad": 5,
        # spines: open frame (top/right off everywhere; left toggled per-chart)
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": True, "axes.spines.bottom": True,
        "axes.edgecolor": EDGE, "axes.linewidth": 0.8,
        # grid: faint, horizontal, behind data
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.7,
        "axes.axisbelow": True,
        # backgrounds: clean white
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        # editorial colorblind-safe cycle
        "axes.prop_cycle": mpl.cycler(color=CATEGORICAL),
        # lines / markers
        "lines.linewidth": 2.2, "lines.solid_capstyle": "round", "lines.markersize": 6,
        # crisp, font-embedded output
        "figure.dpi": 100, "savefig.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.3,
        "svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42,
        "axes.unicode_minus": False,
    })
    _applied = True


# --- layout helpers ---------------------------------------------------------------

def title_block(fig, title, subtitle=None, source=None, kicker=None,
                kicker_color=CLARET, x=0.045, top=0.965):
    """Left-aligned title block in figure coords (aligns to the figure, not the axes -- the
    key tell vs suptitle): a colored kicker rule + UPPERCASE category tag, a bold claim
    headline, a grey dek, and a grey source line bottom-left. Call after laying out axes;
    reserve room with fig.subplots_adjust(top=~0.78) so it sits in the gap above the plot."""
    # Vertical gaps are in TYPOGRAPHIC POINTS (converted to figure fraction via the figure height),
    # so title->subtitle spacing is constant on the page for ANY figure height -- it neither
    # collapses/overlaps on a short figure (e.g. a 1-2 row table) nor over-spaces on a tall one
    # (e.g. the dashboard). At the common ~5in editorial height these match the old fixed fractions.
    h = float(fig.get_figheight()) or 5.0

    def _pt(p):
        return (p / 72.0) / h

    y = top
    if kicker:
        fig.add_artist(plt.Line2D([x, x + 0.06], [y, y], color=kicker_color, lw=3,
                                  solid_capstyle="butt", transform=fig.transFigure))
        fig.text(x, y - _pt(6), kicker.upper(), color=kicker_color, fontsize=9,
                 fontweight="bold", ha="left", va="top")
        y -= _pt(18)
    fig.text(x, y, title, fontsize=15, fontweight="bold", color=INK, ha="left", va="top")
    # wrap=True wraps long deks/source notes to the figure width instead of overflowing the
    # canvas -- with savefig.bbox="tight" an unwrapped line would stretch the saved image far
    # wider than the plot, leaving the chart marooned in a thin, over-wide frame.
    if subtitle:
        fig.text(x, y - _pt(17), subtitle, fontsize=11, color=SUB, ha="left", va="top", wrap=True)
    if source:
        fig.text(x, 0.008, source, fontsize=8, color=MUTE, ha="left", va="bottom", wrap=True)


def clean(ax, left=False, grid="y"):
    """Standard chrome removal: drop top/right (and left unless asked), no tick marks, faint
    single-direction grid behind the data."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_color(EDGE)
    ax.tick_params(length=0)
    ax.set_axisbelow(True)
    if grid:
        ax.grid(True, axis=grid, color=GRID, lw=0.7)
        ax.grid(False, axis=("x" if grid == "y" else "y"))
    else:
        ax.grid(False)


def zero_line(ax, axis="y", value=0.0):
    """A considered zero reference for signed data."""
    (ax.axhline if axis == "y" else ax.axvline)(value, color=EDGE, lw=1.0, zorder=1.5)


def label_ends(ax, points, dx=6, min_gap=None):
    """Direct end-of-line labels in the series color (kills the legend box). points: iterable
    of (x, y, text, color). Caller should widen the right margin to fit. When ``min_gap`` (in
    y-data units) is given, labels that would collide are nudged apart vertically (text only --
    they still read by color), so converging lines stay legible."""
    pts = list(points)
    ys = [p[1] for p in pts]
    if min_gap:
        order = sorted(range(len(pts)), key=lambda i: pts[i][1])
        cur = [pts[i][1] for i in order]
        for k in range(1, len(cur)):
            if cur[k] - cur[k - 1] < min_gap:
                cur[k] = cur[k - 1] + min_gap
        for k, i in enumerate(order):
            ys[i] = cur[k]
    for (x, _y, text, color), y in zip(pts, ys):
        ax.annotate(text, (x, y), xytext=(dx, 0), textcoords="offset points",
                    color=color, fontsize=10, fontweight="medium", va="center", ha="left")


def signed(vals, gain=GAIN, loss=LOSS):
    """Diverging color per value sign (gains vs losses)."""
    return [loss if v < 0 else gain for v in vals]


def signed_pct(v, vals=None, *, unit="%"):
    """Signed label for `v` with precision ADAPTIVE to the series magnitude, and no negative-zero.
    Pass `vals` (the whole series) so every label in a chart shares one precision: tiny real effects
    (~0.01%) then read as +0.007 / +0.015 instead of all collapsing to '+0.01', and a value that
    rounds to zero reads '0%' rather than a misleading '-0.00'. This is the design guide's
    "magnitude as a computed number" rule made flexible to ANY result magnitude (tiny real or large
    illustrative); reuse it wherever a bar/point value is stamped so the deck stays legible either way."""
    ref = np.ravel(vals if vals is not None else [v])
    finite = [abs(float(x)) for x in ref if x is not None and np.isfinite(x)]
    m = max(finite, default=0.0)
    d = 2 if m >= 0.1 else 3 if m >= 0.01 else 4 if m > 0 else 2
    r = round(float(v), d)
    return f"0{unit}" if r == 0 else f"{r:+.{d}f}{unit}"


# --- honest, scenario-portable wording -------------------------------------------
# A figure must never ASSERT a result that holds only for one run. Numbers may be stamped
# on a figure (they are computed from the data); DIRECTION and MAGNITUDE words must be
# DERIVED from those numbers, never hardcoded. These helpers centralize that, so titles can
# default to neutral descriptions and any derived phrasing is true by construction for any
# scenario. The country/scenario identity rides in the title and the run directory, so the
# source credit stays model-generic.

SRC = "Source: OG-Core x CLEWS coupled model · author's calculations"


def source_line(note=None, *, base=SRC, extra=None):
    """Grey credit line: `base`, an optional methodology caveat (`extra`, e.g. the CEV-felicity
    note), then the per-run caveat (`note`), joined by '.  '. The one place the credit-line join
    lives, so builders never hand-roll the `SRC + note` f-string. Pass base=<gbd source> to credit
    a different dataset."""
    return ".  ".join(p for p in (base, extra, note) if p)


# OG-Core's default 7-group lifetime-income partition (lambdas [.25,.25,.2,.1,.1,.09,.01]);
# this is the OG-Core default shared across country models, not a PHL-only choice.
_DEFAULT_J7 = ["0-25%", "25-50%", "50-70%", "70-80%", "80-90%", "90-99%", "Top 1%"]


def income_labels(J, lambdas=None):
    """Percentile labels for J lifetime-income groups. Derived from `lambdas` (population
    shares) when given, so they match the run's actual partition; else the OG-Core default-7
    labels for J==7, else generic 'group N'."""
    if lambdas is not None and len(lambdas) == J:
        try:                                              # reuse OG-Core's own labeller (same text)
            from ogcore.output_plots import lambda_labels as _ll
            d = _ll(np.asarray(lambdas, dtype=float))
            return [d[i] for i in range(J)]
        except Exception:  # noqa: BLE001 -- ogcore absent/changed: fall back to the local derivation
            pass
        edges = np.concatenate([[0.0], np.cumsum(np.asarray(lambdas, dtype=float))]) * 100
        out = []
        for a, b in itertools.pairwise(edges):
            lo, hi = round(float(a)), round(float(b))
            out.append(f"Top {100 - lo}%" if (hi >= 99.5 and lo >= 90) else f"{lo}-{hi}%")
        return out
    if J == 7:
        return list(_DEFAULT_J7)
    return [f"group {i + 1}" for i in range(J)]


def retire_age(params, default=None):
    """OG-Core retirement AGE from a model_params object. Prefers ``retirement_age`` (already an
    age, e.g. 65); else converts ``retire`` (a lifecycle index counted from the start age E) via
    E + retire. Returns ``default`` (None) when neither is present -- callers should omit the
    marker rather than guess a value."""
    ra = getattr(params, "retirement_age", None)
    if ra is not None:
        try:
            return int(np.atleast_1d(ra).flat[0])
        except Exception:  # noqa: BLE001
            pass
    retire, E = getattr(params, "retire", None), getattr(params, "E", None)
    if retire is not None and E is not None:
        try:
            return int(np.atleast_1d(E).flat[0]) + int(np.atleast_1d(retire).flat[0])
        except Exception:  # noqa: BLE001
            pass
    return default


def pct_dev(reform, base):
    """Signed %-deviation of reform vs base (element-wise), NaN where base is zero. The one place
    the (reform-base)/base formula lives, so every builder reports deviations identically."""
    base = np.asarray(base, dtype=float)
    reform = np.asarray(reform, dtype=float)
    return 100.0 * (reform - base) / np.where(base == 0, np.nan, base)


def mark_retirement(ax, params, *, label_top=True, color=SUB):
    """Dashed vertical marker + 'retirement' label at the model's retirement age (via retire_age),
    drawn only if the run provides one (else a no-op returning None). Centralizes the marker the
    lifecycle builders share. Returns the age, or None when absent."""
    age = retire_age(params)
    if age is None:
        return None
    ax.axvline(age, color=color, lw=0.9, ls=(0, (4, 3)), zorder=2)
    y = ax.get_ylim()[1] if label_top else ax.get_ylim()[0]
    ax.annotate("retirement", (age, y), xytext=(5, -4 if label_top else 6),
                textcoords="offset points", fontsize=8.5, color=color,
                va="top" if label_top else "bottom")
    return age


def save(fig, path):
    fig.savefig(path)
    plt.close(fig)
    return path
