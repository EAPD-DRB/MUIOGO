"""Demographic helpers: pure, in-repo, numpy-only at the math level, so the solve path runs on any
checkout without machine-bound paths.

Provenance (all three functions are dependency-light, numpy-only at the math level):
  * ``total_deaths`` — a faithful copy of the standard get_pop_data construction (verified).
  * ``extrapolate_demographics`` — the standard ``get_pop_data`` construction (the brentq calibration
    in :mod:`oglink.health_pop` reuses it, so the construction matches the published method).
  * ``baseline_pop`` — a thin, UNIVERSAL wrapper over ``ogcore.demographics`` that mirrors the
    country model's OWN ``get_pop_objs`` call (ogcore convention), so the link never reinvents
    demographics. ``ogcore`` is imported lazily inside it so importing ``oglink`` stays
    numpy-only for the transform tests.
"""
from __future__ import annotations

import os

import numpy as np


def total_deaths(pop_dist, fert_rates, mort_rates, infmort_rates, imm_rates, num_years=200):
    """Total deaths each year for ``num_years`` (forward cohort iteration). Returns a
    (num_years, n_ages) array. Verbatim from the standard ``get_pop_data.total_deaths``."""
    initial_years = mort_rates.shape[0]
    deaths = np.zeros((num_years, mort_rates.shape[1]))
    pop_t = pop_dist[0, :]
    for y in range(initial_years):
        deaths[y, :] = pop_t * mort_rates[y, :]
        pop_tp1 = np.zeros_like(pop_t)
        pop_tp1[1:] = pop_t[:-1] * (1 - mort_rates[y, :-1]) + pop_t[:-1] * imm_rates[y, :-1]
        pop_tp1[0] = (pop_t * fert_rates[y, :]).sum() * (1 - infmort_rates[y])
        pop_t = pop_tp1
    for yy in range(initial_years, num_years):
        deaths[yy, :] = pop_t * mort_rates[-1, :]
        pop_tp1 = np.zeros_like(pop_t)
        pop_tp1[1:] = pop_t[:-1] * (1 - mort_rates[-1, :-1]) + pop_t[:-1] * imm_rates[-1, :-1]
        pop_tp1[0] = (pop_t * fert_rates[-1, :]).sum() * (1 - infmort_rates[-1])
        pop_t = pop_tp1
    return deaths


def extrapolate_demographics(rates, num_years):
    """Extend a demographic rate path (year on axis 0) to ``num_years`` rows by repeating the
    final observed row. Verbatim from the standard ``get_pop_data.extrapolate_demographics``."""
    if rates.shape[0] >= num_years:
        return rates[:num_years].copy()
    extra_rows = np.repeat(rates[-1:], num_years - rates.shape[0], axis=0)
    return np.concatenate((rates, extra_rows), axis=0)


def baseline_pop(p, un_country_code, download_path):
    """Baseline population objects via ``ogcore.demographics`` — a thin, UNIVERSAL wrapper that
    mirrors the country model's OWN ``get_pop_objs`` call so the link never reinvents demographics.
    ``un_country_code`` is the package's ``UN_COUNTRY_CODE`` (always discovered + passed by og_runner;
    never hardcoded). ogcore fetches from the UN data portal and falls back to the github
    EAPD-DRB/Population-Data repo, writing the raw CSVs to ``download_path`` (a per-run cache).

    The window is ogcore's own convention: ``initial_data_year = start_year - 1`` (the PRE-PERIOD year),
    ``final_data_year = start_year + 1`` — IDENTICAL to what the country model's calibration uses
    (e.g. ogphl/calibrate.py: ``get_pop_objs(p.E, p.S, p.T, 0, 99, country_id=UN_COUNTRY_CODE,
    initial_data_year=p.start_year - 1, final_data_year=p.start_year + 1, ...)`` with NO rates and NO
    pop_dist passed — ogcore fetches + infers internally). Passing ``initial_data_year = start_year``
    (the link's old choice) left the inferred ``g_n`` growth-rate path shifted by a year; this matches
    the country baseline exactly.

    We ALSO fetch the raw rate inputs over the SAME window (``get_pop``/``get_fert``/``get_mort``/
    ``get_imm_rates`` with start_year=start_year-1, end_year=start_year+1) for ``total_deaths`` and the
    health channel's mortality-shock aux — these do not feed back into ``get_pop_objs`` (it fetches its
    own), they are only the rate aux :mod:`oglink.health_pop` needs.

    Returns the 8-tuple
    ``(pop_dict, pop_dist, pre_pop_dist, fert_rates, mort_rates, infmort_rates, imm_rates, deaths)``.
    ``pre_pop_dist`` is the leading (start_year-1) row, kept only to preserve the return contract /
    ``_pop_aux`` (no consumer feeds it back to get_pop_objs). ``ogcore`` is imported lazily so this
    module stays numpy-only at import time."""
    from ogcore import demographics

    os.makedirs(download_path, exist_ok=True)
    s0, s1 = p.start_year - 1, p.start_year + 1
    pop_dist = demographics.get_pop(
        p.E, p.S, 0, 99, country_id=un_country_code,
        start_year=s0, end_year=s1, download_path=download_path)
    pre_pop_dist = pop_dist[:1, :].copy()   # leading (pre-period) row -- contract only; see docstring
    fert_rates = demographics.get_fert(
        p.E + p.S, 0, 99, country_id=un_country_code,
        start_year=s0, end_year=s1, graph=False, download_path=download_path)
    mort_rates, infmort_rates = demographics.get_mort(
        p.E + p.S, 0, 99, country_id=un_country_code,
        start_year=s0, end_year=s1, graph=False, download_path=download_path)
    imm_rates = demographics.get_imm_rates(
        p.E + p.S, 0, 99, country_id=un_country_code, fert_rates=fert_rates,
        mort_rates=mort_rates, infmort_rates=infmort_rates, pop_dist=pop_dist,
        start_year=s0, end_year=s1, graph=False, download_path=download_path)

    deaths = total_deaths(pop_dist, fert_rates, mort_rates, infmort_rates, imm_rates, num_years=200)
    # Mirror the country model's OWN canonical call EXACTLY (ogcore convention): pass ONLY the model
    # dimensions + country_id + the start_year-1 .. start_year+1 window, and let ogcore fetch + infer
    # the population and rates internally. Passing our own fetched rates/pop_dist here is what shifted
    # the baseline g_n away from the country model's; this restores the exact match.
    pop_dict = demographics.get_pop_objs(
        p.E, p.S, p.T, 0, 99, country_id=un_country_code,
        initial_data_year=s0, final_data_year=s1, GraphDiag=False, download_path=download_path)
    return (pop_dict, pop_dist, pre_pop_dist, fert_rates, mort_rates, infmort_rates, imm_rates, deaths)
