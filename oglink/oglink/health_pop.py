"""Bidirectional ``disease_pop``: the published age-profile mortality method, generalized so the
excess-deaths target may be NEGATIVE (lives saved -- the cleaner-air / pollution direction) as well
as positive (the HIV / disease-burden direction the published code handles).

    rho(s,t) = rho0(s,t) + shock_scale * h(s) * t/phase_years          (clipped to [0, 1])

for the ``phase_years`` MODEL years, where ``t`` runs 1..phase_years. The rate arrays carry a leading
PRE-PERIOD row (year start_year-1, the ogcore data window's first row) that is NEVER shocked -- you
cannot shock history -- so the ramp lands on rows 1..phase_years and row 0 stays at the baseline rate.

``shock_scale`` is solved so the realized year-``phase_years`` excess deaths equal the (signed)
target; then the population path is recomputed with the built-in ``ogcore.demographics.get_pop_objs``.
The demographic helpers (``total_deaths`` / ``extrapolate_demographics``) live in
:mod:`oglink._demog` (the standard construction), so this module is self-contained.

Two generalizations over the published ``disease_pop``: a 0.0 floor (so a reduction can't drive a
rate negative) and a signed root search that does not assume monotonicity. The realized
year-``phase_years`` excess-deaths curve need NOT be monotone in ``shock_scale`` (survivorship
feedback: people whose deaths are averted in early years age into other mortality bands; the 0.0 clip
saturates), so the search scans a geometric grid outward from 0 and brackets the FIRST sign change --
the smallest-magnitude shock that hits the target -- then reports the true achievable extremum if the
target is infeasible. This is correct whenever the curve is monotone up to the first root (the
realistic mortality case) and tolerates a turn-around after it; it does not chase a second root that
rises and falls entirely within one grid interval (not a regime real age profiles produce).
"""
from __future__ import annotations

import numpy as np

from ._demog import extrapolate_demographics, total_deaths

# Geometric |scale| grid scanned outward from 0: fine near 0 (catches ~1e-4 roots) up to a cap.
_MIN_MAG = 1e-6
_MAX_MAG = 1e6


def calibrate_shock_scale(target, pop_dist, fert, mort, infmort, imm, profile, phase_years,
                          total_deaths_fn=total_deaths):
    """Solve the additive age-profile shock scale that hits a SIGNED year-``phase_years``
    excess-deaths target. ``target > 0`` adds deaths (positive scale); ``target < 0`` saves lives
    (negative scale); ``target == 0`` is a no-op. Returns ``(shock_scale, shocked_mortality_path)``.
    Pure -- no ogcore. Robust to a non-monotone gap (see module docstring).

    The mortality arrays carry a LEADING PRE-PERIOD row (year start_year-1): row 0 is the pre-period
    and is NEVER shocked, and the ramp covers the ``phase_years`` MODEL years on rows 1..phase_years
    (so ``mort`` has ``phase_years + 1`` rows). The target is the realized excess at the LAST model
    year (row ``phase_years``); deaths are iterated over ``phase_years + 1`` years so the unshocked
    pre-period contributes identically to the baseline and shocked paths and cancels out of the
    marginal."""
    from scipy.optimize import brentq

    profile = np.asarray(profile, dtype=float)
    if profile.ndim != 1 or np.any(profile < 0) or not np.all(np.isfinite(profile)):
        raise ValueError("disease_pop: profile must be a finite, nonnegative 1-D age shape "
                         "(a negative h(s) would let the shock add deaths where it should remove them).")
    ny = phase_years
    nyears = ny + 1                                   # 1 pre-period row + ny model-year rows
    base_d = total_deaths_fn(pop_dist, fert, mort, infmort, imm, num_years=nyears)[ny].sum()

    def shock_path(scale):
        alt = mort.copy()
        # row 0 = pre-period (start_year-1): left UNSHOCKED -- you can't shock history. The ramp lands
        # on the ny model-year rows 1..ny, reaching full strength at the last model year.
        for t in range(1, nyears):
            alt[t, :] = np.clip(mort[t, :] + scale * profile * (t / ny), 0.0, 1.0)
        return alt

    def gap(scale):  # realized year-ny (last MODEL year) excess deaths minus the target (root at gap == 0)
        d = total_deaths_fn(pop_dist, fert, shock_path(scale), infmort, imm, num_years=nyears)
        return d[ny].sum() - base_d - target

    if target == 0:
        return 0.0, shock_path(0.0)

    direction = 1.0 if target > 0 else -1.0
    # Scan outward from 0 on the correct half-line; brentq the FIRST sign-change sub-interval so the
    # smallest-magnitude root is returned even if the gap curve later turns around.
    mags = []
    mag = _MIN_MAG
    while mag < _MAX_MAG:
        mags.append(mag)
        mag *= 2.0
    mags.append(_MAX_MAG)                  # ensure the scan actually reaches the cap
    prev_s, prev_g = 0.0, gap(0.0)        # gap(0) == -target (opposite sign to the search direction)
    best_excess = 0.0                     # most extreme realized excess seen, in the search direction
    for mag in mags:
        s = direction * mag
        gs = gap(s)
        realized = gs + target            # realized excess deaths at this scale
        best_excess = max(best_excess, realized) if direction > 0 else min(best_excess, realized)
        if gs == 0.0:
            return s, shock_path(s)
        if np.sign(gs) != np.sign(prev_g):
            scale = brentq(gap, prev_s, s)
            return scale, shock_path(scale)
        prev_s, prev_g = s, gs

    kind = "added" if direction > 0 else "avertable"
    raise RuntimeError(
        f"disease_pop: target {target:+,.0f} exceeds the achievable {kind} deaths for this profile "
        f"(max ~= {best_excess:+,.0f}); the age shape cannot reach it even fully saturated.")


def disease_pop(p, aux, excess_deaths, profile, phase_years=5, *, un_country_code):
    """Recompute the population under a (signed) excess-deaths age-profile mortality shock.

    ``aux`` is the stashed baseline demographic dict (pop_dist, fert_rates, mort_rates, infmort_rates,
    imm_rates) produced by :func:`oglink._demog.baseline_pop`. Because that wrapper now uses
    ogcore's window convention, the FIRST row of every rate array is the PRE-PERIOD year
    (start_year-1) and ``aux["pop_dist"][0]`` is that pre-period population row. Returns
    ``(pop_dict, shock_scale)``: the pop_dict goes straight into ``p.update_specifications(...)`` before
    solving, as the published method does.

    The get_pop_objs call passes the SHOCKED mortality (so it stays a pass-rates inference), aligned to
    ogcore's convention: ``initial_data_year = start_year - 1`` (the pre-period), ``final_data_year =
    start_year + ny - 1``, giving ``T0 = ny + 1`` data rows -- the leading pre-period row plus the ``ny``
    model years. The rate arrays are extrapolated to that T0; ``calibrate_shock_scale`` leaves the
    pre-period row unshocked and ramps the ny model years.

    IMPORTANT -- this omega is NOT comparable to :func:`oglink._demog.baseline_pop`'s omega. This
    call uses ``infer_pop=True`` seeded from a SINGLE population row with ``final_data_year =
    start_year + ny - 1`` (T0 = ny+1); ``baseline_pop`` uses ``infer_pop=False`` with ``final_data_year =
    start_year + 1`` (T0 = 3), letting ogcore fetch the OBSERVED multi-year UN population. Differencing
    the two omegas is dominated by that construction mismatch (single-age age-heaping + a window kink),
    ~1000x larger than and orthogonal to the mortality signal. The CLEAN mortality marginal is THIS
    shocked omega minus a ZERO-shock ``disease_pop`` omega (same window, same seed, same inference -- only
    ``mort_rates`` differs); that difference is smooth and tracks the age profile. Never diff the shocked
    omega against ``baseline_pop``'s omega."""
    from ogcore import demographics

    ny = int(phase_years)
    nyears = ny + 1                                   # T0 = ny model years + 1 leading pre-period row
    fert = extrapolate_demographics(np.asarray(aux["fert_rates"], dtype=float), nyears)
    mort = extrapolate_demographics(np.asarray(aux["mort_rates"], dtype=float), nyears)
    imm = extrapolate_demographics(np.asarray(aux["imm_rates"], dtype=float), nyears)
    infmort = extrapolate_demographics(np.asarray(aux["infmort_rates"], dtype=float), nyears)
    pop_dist = np.asarray(aux["pop_dist"], dtype=float)

    h = np.asarray(profile, dtype=float)
    nage = mort.shape[1]
    if h.shape[0] != nage:                 # match the profile to the model's age dimension
        h = np.interp(np.linspace(0, 1, nage), np.linspace(0, 1, h.shape[0]), h)

    scale, alt_mort = calibrate_shock_scale(
        float(excess_deaths), pop_dist, fert, mort, infmort, imm, h, ny, total_deaths)

    # ogcore convention: initial_data_year = start_year - 1 (the pre-period row), final_data_year =
    # start_year + ny - 1 -> T0 = ny + 1 = the leading pre-period row plus the ny model years. Seed the
    # infer_pop recursion with pop_dist's leading (start_year-1) row and feed the SHOCKED mort path. The
    # clean mortality marginal is THIS omega minus a ZERO-shock disease_pop omega (SAME window/seed/
    # inference, only mort_rates differs on the ny model rows -- the pre-period row 0 is unshocked). NB:
    # this is NOT baseline_pop's window/inference (see the docstring); do not diff against that omega.
    pop_dict = demographics.get_pop_objs(
        p.E, p.S, p.T, 0, 99, country_id=un_country_code,
        fert_rates=fert, mort_rates=alt_mort, infmort_rates=infmort, imm_rates=imm,
        infer_pop=True, pop_dist=pop_dist[:1, :],
        initial_data_year=p.start_year - 1, final_data_year=p.start_year + ny - 1, GraphDiag=False)
    return pop_dict, scale
