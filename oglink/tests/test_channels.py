"""Transform-level tests: exercise every channel's math on array fixtures (no ogcore, no
solve) and the real CLEWS readers against actual files. Run with the OG-PHL venv:

    PYTHONPATH=/Users/mlafleur/Projects/oglink \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python tests/test_channels.py
"""
from __future__ import annotations

import os
import types

import numpy as np

from oglink import channels, experiments, report, signals
from oglink.contract import Concordance
from oglink.country import PHL
from oglink.framework import ExperimentContext, preflight

T, S, J, M, I = 20, 8, 7, 4, 5
TS = T + S
# The energy good/industry indices the fixtures below are built around. The real concordance is now
# DISCOVERED PER RUN (ctx.concordance, exported from the OG env), not a country-config literal; these
# transform tests pin one so the channel math runs against a known, isolated energy port.
I_E, M_E = 1, 1
CONCORDANCE = Concordance(energy_industry_index=M_E, energy_good_index=I_E)
HAVE_CLEWS = os.path.isdir(PHL.scenario.base_dir) and os.path.isdir(PHL.scenario.reform_dir)
_MUIOGO_RUN = "/Users/mlafleur/Projects/MUIOGO/WebAPP/DataStorage/CLEWs Demo/res/REF"
_GBD_HIV_CSV = ("/Users/mlafleur/Projects/CostOfDisease/source/JDE/hiv-data/"
                "IHME-GBD_2023_DATA-ddf37f70-1/IHME-GBD_2023_DATA-ddf37f70-1.csv")


def _params():
    io = np.full((I, M), 0.25)
    io[I_E, M_E] = 0.107
    return types.SimpleNamespace(
        T=T, J=J, M=M, I=I, baseline=False,
        tau_c=np.full((TS, I), 0.12), Z=np.ones((TS, M)),
        gamma=np.full(M, 0.53785), gamma_g=np.full(M, 0.05),   # per-industry, time-invariant (1-D, M)
        alpha_I=np.full(TS, 0.02), alpha_T=np.full(TS, 0.05), alpha_bs_I=np.ones(TS),
        c_min=np.zeros(I), e=np.ones((T, S, J)), chi_n=np.ones((TS, S)), io_matrix=io,
        inv_tax_credit=np.zeros((TS, M)), delta_tau=np.zeros((TS, M)), tau_b=np.full((TS, M), 0.25))


def _tpi(scale=1.0):
    return {"C_i": np.full((T, I), 10.0) * scale, "p_i": np.full((T, I), 1.0),
            "Y": np.full(T, 100.0), "Y_m": np.full((T, M), 25.0) * scale,
            "c_i": np.ones((T, I, S, J)) * scale, "c": np.ones((T, S, J)) * scale,
            "r_p": np.full(T, 0.05), "cons_tax_revenue": np.full(T, 1.0),  # (T,) like real OG
            "resource_constraint_error": np.full(T, 1e-6)}


def _ctx(with_reform=False):
    ctx = ExperimentContext(country=PHL, concordance=CONCORDANCE, og_reform=_params(), base_tpi=_tpi(1.0))
    if with_reform:
        ctx.reform_tpi = _tpi(1.05)  # +5% activity
    return ctx


# --- tests ----------------------------------------------------------------------

def test_registry():
    for name in ["energy_price", "investment", "capital_intensity", "energy_capex", "carbon_tax",
                 "emit_carbon_penalty", "emit_discount_rate", "health", "emit_energy_demand"]:
        assert callable(getattr(channels, name)), name


def test_energy_capex_itc():
    # the ITC (capital-demand) channel applies an investment tax credit to the ENERGY industry only
    ctx = _ctx()
    channels.energy_capex(ctx, investment_tax_credit_rate=0.20)
    itc = ctx.og_reform.inv_tax_credit
    assert itc[0, M_E] == 0.20
    assert all(itc[0, m] == 0.0 for m in range(M) if m != M_E)


def test_energy_price_controlled():
    ctx = _ctx()
    prov = channels.energy_price(ctx, price_ratio=1.20)
    tau = np.asarray(ctx.og_reform.tau_c)[0, I_E]
    assert abs((1 + tau) - 1.20 * 1.12) < 1e-9, (tau, prov)  # (1+tau_new) = ratio*(1+tau_base)


def test_energy_price_recycle_bumps_transfers():
    ctx = _ctx()
    a0 = np.asarray(ctx.og_reform.alpha_T).copy()
    prov = channels.energy_price(ctx, price_ratio=1.20, recycle_revenue_to_transfers=True)
    assert prov["recycled_pct_gdp"] is not None and prov["recycled_pct_gdp"] > 0
    assert np.asarray(ctx.og_reform.alpha_T)[0] > a0[0]


def test_energy_price_cmin():
    ctx = _ctx()
    channels.energy_price(ctx, price_ratio=1.10, energy_subsistence_floor=0.005)
    assert np.asarray(ctx.og_reform.c_min)[I_E] == 0.005


def test_ss_tail_persistence(monkeypatch):
    # permanent policy (carbon tax, recycled transfers) must reach the SS tail T:T+S;
    # temporary transition capex (investment) must taper to baseline there.
    ctx = _ctx()
    channels.carbon_tax(ctx, carbon_price_usd_per_tco2=50.0, carbon_per_energy_unit=0.01, recycle_revenue_to_transfers=False)
    assert np.asarray(ctx.og_reform.tau_c)[-1, I_E] > 0.12, "carbon tau_c must persist into SS tail"
    ctx2 = _ctx()
    channels.energy_price(ctx2, price_ratio=1.20, recycle_revenue_to_transfers=True)
    assert np.asarray(ctx2.og_reform.alpha_T)[-1] > 0.05, "recycled alpha_T must persist into SS tail"
    # investment is public-infra-only and PHL/PEP has ~0 grid capex, so inject a synthetic non-zero
    # public-infra increment to actually exercise the finite-flow taper.
    import pandas as pd

    from oglink import signals as _sig
    yrs = list(range(2026, 2054))
    monkeypatch.setattr(_sig, "power_capex_increment", lambda *a, **k: pd.Series([5000.0] * len(yrs), index=yrs))
    ctx3 = _ctx()
    a0 = np.asarray(ctx3.og_reform.alpha_I).copy()
    capex = _sig.public_capex_pct_gdp(PHL.scenario.base_dir, PHL.scenario.reform_dir, PHL,
                                      og_start_year=PHL.scenario.og_start_year, T=ctx3.og_reform.T)
    channels.investment(ctx3, capex, persist_into_steady_state=False)
    assert np.asarray(ctx3.og_reform.alpha_I)[-1] == a0[-1], "temporary investment must taper in SS tail"
    assert not np.allclose(np.asarray(ctx3.og_reform.alpha_I)[:5], a0[:5]), "transition years must move"


def test_empty_signal_no_crash():
    import pandas as pd

    from oglink.signals import _align_to_start, _fit
    assert _fit(np.array([]), 5).shape == (5,)                 # empty -> zeros, no IndexError
    s = pd.Series([1.0, 1.1], index=[2020, 2021])
    assert _align_to_start(s, 2026, 8).shape == (8,)           # start_year past the series -> zeros


def test_carbon_both_sides():
    ctx = _ctx()
    # units-sane illustrative intensity (50 USD/tCO2 * 0.005 = 25% add-on, < the 100% hard-block)
    channels.carbon_tax(ctx, carbon_price_usd_per_tco2=50.0, carbon_per_energy_unit=0.005, recycle_revenue_to_transfers=True)
    channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)
    assert np.asarray(ctx.og_reform.tau_c)[0, I_E] > 0.12          # OG carbon tax raised energy tau_c
    assert "EmissionsPenalty" in ctx.clews_inputs                  # CLEWS side written


def test_carbon_blocks_absurd_tax():
    import pytest
    # carbon_per_energy_unit=0.5 with the uncalibrated deflator implies a ~2500% tau_c -> must hard-raise,
    # not silently apply a meaningless tax.
    with pytest.raises(ValueError):
        channels.carbon_tax(_ctx(), carbon_price_usd_per_tco2=50.0, carbon_per_energy_unit=0.5)
    # ...but an explicit illustrative override is allowed:
    ctx = _ctx()
    channels.carbon_tax(ctx, carbon_price_usd_per_tco2=50.0, carbon_per_energy_unit=0.5, allow_illustrative_magnitude=True)
    assert np.asarray(ctx.og_reform.tau_c)[0, I_E] > 0.12


def test_discount_rate_postsolve():
    ctx = _ctx(with_reform=True)  # the emit_ channel forwards the REFORM equilibrium rate
    prov = channels.emit_discount_rate(ctx, og_rate_series="market_return")
    assert ctx.clews_inputs["DiscountRate"]["rate"] == 0.05
    assert prov["clews_discount_rate"] == 0.05


def test_demand_postsolve():
    ctx = _ctx(with_reform=True)
    ar = signals.activity_ratio(ctx.base_tpi, ctx.reform_tpi, driver="Y_m", og_index=M_E)
    prov = channels.emit_energy_demand(ctx, ar, og_activity="sector_output")
    assert abs(prov["mean_ratio"] - 1.05) < 1e-9                   # +5% activity -> +5% demand
    assert "Demand" in ctx.clews_inputs


def test_clews_io_roundtrip():
    # guards the channel-artifact <-> clews_io key coupling (clews_io has no other coverage): every
    # og->clews / policy artifact the channels emit must serialize with the keys clews_io reads.
    import tempfile

    from oglink import clews_io
    ctx = _ctx(with_reform=True)
    ar = signals.activity_ratio(ctx.base_tpi, ctx.reform_tpi, driver="Y_m", og_index=M_E)
    channels.emit_energy_demand(ctx, ar, og_activity="sector_output")
    channels.emit_discount_rate(ctx)
    channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)
    with tempfile.TemporaryDirectory() as d:
        written = clews_io.write_all(ctx, d)
    assert set(written) == {"Demand", "DiscountRate", "EmissionsPenalty"}


def test_experiments_run_through_with_fake_solve():
    # the experiment FUNCTIONS aren't otherwise unit-tested; run each with a no-op solve so the recipe
    # (pre-solve channels, the signals sourcing, the emit_* post-solve calls) executes without a real OG
    # solve -- catches NameErrors / arg mismatches in the recipe layer (e.g. a broken _activity helper).
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    from oglink import experiments

    def fake_solve(ctx):
        ctx.reform_tpi = ctx.base_tpi          # no OG solve; just satisfy the post-solve emit channels
        return ctx.reform_tpi
    for name in experiments.names():
        ctx = _ctx(with_reform=True)
        experiments.get(name)(ctx, fake_solve)  # must not raise


def test_guardrails_present():
    assert preflight(["carbon_tax", "emit_carbon_penalty"])       # one-price discipline message
    assert preflight(["energy_price", "carbon_tax"])              # double-count warning


def test_investment_public_infra_only():
    # public-infra-only: only genuine grid (T&D) capex flows to alpha_I; private generation capex is
    # excluded (its macro effect rides the energy channel). Under CLEWS v9 the PEP reform has a SMALL
    # T&D build, so alpha_I moves slightly -- NOT the exact zero of the retired v6 pair. The invariant
    # tested is that public_only keeps the effect SMALL and bounded, never a large public-investment shock.
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    ctx = _ctx()
    a0 = np.asarray(ctx.og_reform.alpha_I).copy()
    capex = signals.public_capex_pct_gdp(PHL.scenario.base_dir, PHL.scenario.reform_dir, PHL,
                                         og_start_year=PHL.scenario.og_start_year, T=ctx.og_reform.T)
    prov = channels.investment(ctx, capex)
    assert "cumulative_pct_gdp" in prov
    assert prov["peak_pct_gdp"] < 1e-3                             # v9 T&D capex delta is small (~1.6e-4)
    assert np.max(np.abs(np.asarray(ctx.og_reform.alpha_I) - a0)) < 1e-3   # alpha_I barely moves (public-infra only)


# --- #2b capital intensity (gamma_energy) lever + calibration + channel ---------

def test_capital_intensity_lever_scale():
    from oglink import policy_levers
    p = _params()
    prov = policy_levers.set_capital_intensity(p, M_E, gamma_scale=1.122)
    assert abs(np.asarray(p.gamma)[M_E] - 0.53785 * 1.122) < 1e-9     # energy gamma scaled
    for m in range(M):                                               # every OTHER industry untouched
        if m != M_E:
            assert abs(np.asarray(p.gamma)[m] - 0.53785) < 1e-12
    # labor share is the residual 1 - gamma - gamma_g (no separate parameter)
    assert abs(prov["labor_share_new"] - (1 - 0.53785 * 1.122 - 0.05)) < 1e-9
    assert prov["mode"] == "scale" and prov["gamma_old"] == 0.53785


def test_capital_intensity_lever_target_and_identity():
    from oglink import policy_levers
    p = _params()
    prov = policy_levers.set_capital_intensity(p, M_E, gamma_target=0.60)
    assert abs(np.asarray(p.gamma)[M_E] - 0.60) < 1e-12
    # gamma + gamma_g + labor == 1 by construction
    assert abs(prov["gamma_new"] + prov["gamma_g"] + prov["labor_share_new"] - 1.0) < 1e-12


def test_capital_intensity_lever_blocks_infeasible():
    import pytest

    from oglink import policy_levers
    # gamma 0.99 + gamma_g 0.05 -> labor share -0.04 < floor: a <=0 labor exponent OG-Core won't catch
    with pytest.raises(ValueError):
        policy_levers.set_capital_intensity(_params(), M_E, gamma_target=0.99)
    with pytest.raises(ValueError):                                  # scale big enough to break the floor
        policy_levers.set_capital_intensity(_params(), M_E, gamma_scale=1.8)
    with pytest.raises(ValueError):                                  # gamma > 1
        policy_levers.set_capital_intensity(_params(), M_E, gamma_target=1.2)


def test_capital_intensity_lever_requires_exactly_one():
    import pytest

    from oglink import policy_levers
    with pytest.raises(ValueError):                                  # neither
        policy_levers.set_capital_intensity(_params(), M_E)
    with pytest.raises(ValueError):                                  # both
        policy_levers.set_capital_intensity(_params(), M_E, gamma_target=0.6, gamma_scale=1.1)


def test_capital_intensity_channel_explicit():
    ctx = _ctx()
    g0 = float(np.asarray(ctx.og_reform.gamma)[M_E])
    prov = channels.capital_intensity(ctx, energy_capital_share_multiplier=1.122)       # caller-sourced scale
    assert float(np.asarray(ctx.og_reform.gamma)[M_E]) > g0
    assert prov["gamma_new"] > prov["gamma_old"]


def test_capital_intensity_validate():
    # single-channel framing now lives in the docstring; cross-channel cautions in preflight()
    assert "factor-SHARE" in (channels.capital_intensity.__doc__ or "")
    msgs2 = preflight(["capital_intensity", "investment"])
    assert any("COMPLEMENTARY" in m for m in msgs2)                  # vs the public-investment channel


def test_capital_cost_share_reader():
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    sb = signals.capital_cost_share(PHL.scenario.base_dir, PHL, window=(2026, 2035))
    sr = signals.capital_cost_share(PHL.scenario.reform_dir, PHL, window=(2026, 2035))
    assert 0.0 < sb < 1.0 and 0.0 < sr < 1.0
    cal = signals.capital_intensity_ratio(PHL.scenario.base_dir, PHL.scenario.reform_dir, PHL)
    assert cal["ratio"] > 1.0                                        # PEP mix more capital-intensive near-term
    assert abs(cal["ratio"] - sr / sb) < 1e-9


def test_capital_intensity_channel_calibrates_from_clews():
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    ctx = _ctx()
    g0 = float(np.asarray(ctx.og_reform.gamma)[M_E])
    cal = signals.capital_intensity_ratio(PHL.scenario.base_dir, PHL.scenario.reform_dir, PHL,
                                          window=(PHL.scenario.og_start_year, PHL.scenario.og_start_year + 9))
    prov = channels.capital_intensity(ctx, energy_capital_share_multiplier=cal["ratio"])  # caller sources from CLEWS
    assert cal["ratio"] > 1.0
    assert float(np.asarray(ctx.og_reform.gamma)[M_E]) > g0 and prov["labor_share_new"] > 0


def test_health_reads_clews():
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    ctx = _ctx()
    e0 = np.asarray(ctx.og_reform.e).copy()
    prov = channels.health(ctx)
    assert "emissions_change" in prov
    shock = ctx.extras.get("health_shock")                        # disease_pop spec for the runtime
    assert shock is not None and "excess_deaths" in shock and len(shock["profile"]) == 100
    assert shock["rc_ss"] == PHL.rc_ss                            # scoped SS tolerance routed to the reform
    assert shock["excess_deaths"] < 0                             # PHL reform is cleaner -> lives saved (negative)
    assert not np.allclose(np.asarray(ctx.og_reform.e), e0)       # morbidity productivity path moved


def test_health_dose_response_multiplier():
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    # M = energy mass share x CRF elasticity scales the power-emissions change to the ambient effect.
    p1 = channels.health(_ctx(), enable_mortality=True, enable_morbidity=False, total_attributable_deaths=43951.0, emissions_to_deaths_multiplier=1.0)
    pm = channels.health(_ctx(), enable_mortality=True, enable_morbidity=False, total_attributable_deaths=43951.0, emissions_to_deaths_multiplier=0.082)
    assert pm["dose_response_M"] == 0.082
    assert abs(pm["mortality_excess_deaths"] / p1["mortality_excess_deaths"] - 0.082) < 1e-9  # linear in M
    # default (no arg) uses the calibrated PHL value from the data file, not the naive 1:1
    dflt = channels.health(_ctx(), enable_mortality=True, enable_morbidity=False, total_attributable_deaths=43951.0)
    assert dflt["dose_response_M"] == PHL.pm25_dose_response and PHL.pm25_dose_response < 0.2


def test_health_skips_when_no_gbd_data(monkeypatch):
    # A fresh clone has no IHME GBD export (it is gitignored). With VALID emissions but no GBD (and no
    # explicit target), health() must SKIP cleanly -- not raise -- so a bare install runs the coupling
    # (energy+investment+carbon) with no health data. (Corrupt/absent emissions are handled earlier, so
    # we feed a valid emissions ratio to reach the GBD guard.)
    import dataclasses

    import pandas as pd
    monkeypatch.setattr(channels.signals, "emissions_ratio", lambda *a, **k: pd.Series([0.9] * 10))
    c = dataclasses.replace(PHL, gbd_burden_csv=None)
    ctx = ExperimentContext(country=c, concordance=CONCORDANCE, og_reform=_params(), base_tpi=_tpi(1.0))
    e0 = np.asarray(ctx.og_reform.e).copy()
    rec = channels.health(ctx)                                # enable_mortality defaults True; no explicit target
    assert rec.get("skipped") is True and "GBD" in rec.get("reason", "")   # skipped, not ValueError
    assert ctx.extras.get("health_shock") is None             # no mortality shock staged
    assert np.allclose(np.asarray(ctx.og_reform.e), e0)       # morbidity path left untouched


def test_health_profile_shape():
    from oglink import health_profile
    h = health_profile.placeholder_profile()
    assert h.shape == (100,) and abs(h.max() - 1.0) < 1e-9        # peak-1 relative shape
    assert h[80] > h[30]                                          # elderly-skewed (pollution mortality)


def test_disease_pop_bidirectional_calibration():
    # Bidirectional brentq: a positive target -> positive shock_scale (add deaths); a negative
    # target -> negative shock_scale (save lives). No OG solve -- pure construction vs the vendored
    # (CostOfDisease) total_deaths. Uses the in-repo _demog, so it actually exercises the dependency
    # (no external-path skip).
    from oglink import _demog, health_pop, health_profile

    # ny model years + 1 leading PRE-PERIOD row (start_year-1): calibrate_shock_scale leaves row 0
    # unshocked and ramps rows 1..ny, measuring the realized excess at the last model year (row ny).
    nage, ny = 100, 5
    nrows = ny + 1
    s = np.arange(nage)
    mort = np.tile(0.001 + 0.004 * (s / 99.0) ** 3, (nrows, 1))   # rises with age, in (0,1)
    fert = np.zeros((nrows, nage)); fert[:, 15:45] = 0.05
    imm = np.zeros((nrows, nage))
    infmort = np.full(nrows, 0.02)
    pop = (1e6 * np.exp(-s / 50.0))[None, :]                       # (1, nage)
    h = health_profile.placeholder_profile(nage)
    base = _demog.total_deaths(pop, fert, mort, infmort, imm, num_years=nrows)[ny].sum()

    for target in (+5000.0, -5000.0):
        scale, path = health_pop.calibrate_shock_scale(
            target, pop, fert, mort, infmort, imm, h, ny, _demog.total_deaths)
        realized = _demog.total_deaths(pop, fert, path, infmort, imm, num_years=nrows)[ny].sum() - base
        assert (scale > 0) == (target > 0), (target, scale)        # scale sign tracks target sign
        assert abs(realized - target) < 1.0, (target, realized)    # brentq hit the signed target
        assert path.min() >= 0.0 and path.max() <= 1.0             # clip floor + ceiling respected
        assert np.array_equal(path[0], mort[0])                    # pre-period row 0 stays UNSHOCKED


def test_disease_pop_nonmonotone_bracketing():
    # REGRESSION: realized year-ny excess deaths are NOT monotone in shock_scale (survivorship
    # feedback + the 0.0 clip), so the max achievable excess is at a FINITE interior scale. The old
    # doubling-walk assumed monotonicity and could (a) falsely reject a feasible target whose only
    # bracket endpoint sits past the turning point, or (b) land on a non-minimal root. The outward
    # scan must return the SMALLEST-|scale| root and report the true achievable extremum on
    # infeasibility. Driven by a controlled non-monotone total_deaths so the curve shape is exact.
    from oglink import health_pop

    # ny model years + 1 leading pre-period row; the ramp reaches full strength on the last row (t/ny=1).
    nage, ny = 8, 3
    nrows = ny + 1
    mort = np.full((nrows, nage), 0.10)
    fert = np.zeros((nrows, nage)); imm = np.zeros((nrows, nage)); infmort = np.zeros(nrows)
    pop = np.full((1, nage), 1.0)
    h = np.ones(nage)                                             # so mean(final-row shock) == 0.1 + scale

    def nonmono(pop, fert, m, infmort, imm, num_years):
        # year-(ny-1) deaths = a parabola in the mean shocked rate x, peaking at x=0.2: excess rises
        # to an interior max at scale=+0.1 then FALLS -- exactly the shape the doubling-walk mishandles.
        x = float(m[-1].mean())
        val = -((x - 0.2) ** 2) * 1e6 + 4e4
        d = np.zeros((num_years, m.shape[1])); d[-1, 0] = val
        return d

    base = nonmono(pop, fert, mort, infmort, imm, ny)[ny - 1].sum()  # x=0.1 -> val 3e4
    # +5000 is reachable on BOTH the rising (scale~0.029) and falling (scale~0.171) branch; the
    # solver must return the smaller-|scale| (rising) root, and must NOT falsely reject it.
    scale, path = health_pop.calibrate_shock_scale(5000.0, pop, fert, mort, infmort, imm, h, ny, nonmono)
    realized = nonmono(pop, fert, path, infmort, imm, ny)[ny - 1].sum() - base
    assert 0.0 < scale < 0.1 and abs(realized - 5000.0) < 1.0, (scale, realized)

    # a target beyond the interior maximum (~1e4 excess) is infeasible -> raise with the achievable max.
    try:
        health_pop.calibrate_shock_scale(5e4, pop, fert, mort, infmort, imm, h, ny, nonmono)
        raise AssertionError("expected RuntimeError for a target past the interior maximum")
    except RuntimeError as e:
        assert "exceeds the achievable" in str(e)


def test_morbidity_age_profile():
    # The morbidity (effective-labor) effect must accept an AGE distribution, mirroring mortality's
    # h(s): a non-uniform shape concentrates the productivity gain by age; the default is uniform.
    from oglink import health_profile
    E, S = 20, 80
    # default in the channel is uniform (np.ones(S) inline -> "all active ages equal"); a non-uniform
    # shape concentrates the gain by age:
    wap = health_profile.working_age_profile(E, S)
    assert wap.shape == (S,) and abs(wap.max() - 1.0) < 1e-9         # peak-1 shape over active periods
    assert wap[:5].mean() < wap[20:40].mean()                       # prime-age weighted above the oldest
    # a full-age-grid (E+S) input maps to the active tail [E:]; arbitrary length interpolates to S
    full = np.linspace(0.0, 1.0, E + S)
    assert health_profile.morbidity_shape_to_S(full, S, E).shape == (S,)
    assert health_profile.morbidity_shape_to_S(np.ones(37), S, E).shape == (S,)


def test_vendored_demog_selfcontained():
    # Portability: the demographic helpers are vendored in-repo (no absolute-path loads of
    # CostOfDisease / CLEWS-OG). They import and run on numpy alone.
    from oglink import _demog
    ny, nage = 5, 100
    mort = np.full((ny, nage), 0.01)
    fert = np.zeros((ny, nage)); fert[:, 20:40] = 0.05
    imm = np.zeros((ny, nage)); infmort = np.full(ny, 0.02)
    pop = np.full((1, nage), 1000.0)
    d = _demog.total_deaths(pop, fert, mort, infmort, imm, num_years=ny)
    assert d.shape == (ny, nage) and np.all(d >= 0)
    assert _demog.extrapolate_demographics(mort[:2], ny).shape == (ny, nage)


def test_gbd_profile_and_total_from_real_export():
    # Validate the GBD readers against a REAL IHME export (HIV/South-Africa stands in for the PHL
    # ambient-PM2.5 pull -- identical format) so the pipeline is proven before the real CSV lands.
    from oglink import health_profile
    if not os.path.isfile(_GBD_HIV_CSV):
        print("  (skip: GBD export absent)"); return
    h = health_profile.build_profile_from_gbd(
        _GBD_HIV_CSV, location_name="South Africa", year=2023,
        key_col="cause_name", key_value="HIV/AIDS")           # PHL PM2.5 -> rei_name/Ambient... instead
    assert h.shape == (100,) and abs(h.max() - 1.0) < 1e-9       # peak-1 age shape from real GBD rates
    tot = health_profile.total_deaths_from_gbd(
        _GBD_HIV_CSV, location_name="South Africa", year=2023,
        key_col="cause_name", key_value="HIV/AIDS")
    assert tot > 0                                               # total deaths (excess_deaths target)


def test_gbd_morbidity_readers_from_real_export():
    # Validate the morbidity YLD readers against the real PHL ambient-PM2.5 GBD export (if present).
    from oglink import health_profile
    csv = PHL.gbd_burden_csv
    if not csv or not os.path.isfile(csv):
        print("  (skip: GBD burden export absent)"); return
    g = health_profile.build_morbidity_profile_from_gbd(csv, "Philippines", 2023)
    assert g.shape == (100,) and abs(g.max() - 1.0) < 1e-9       # peak-1 working-age YLD shape
    assert g[20] < 0.05 and g[25] < g[60] < g[90]               # ~0 young, RISES with age (vs elderly deaths)
    rate = health_profile.morbidity_yld_rate_from_gbd(csv, "Philippines", 2023)
    yld = health_profile.total_yld_from_gbd(csv, "Philippines", 2023)
    assert rate > 0 and yld > 0                                  # magnitude (peak rate) + provenance total


def test_clews_capex_reader():
    if not HAVE_CLEWS:
        print("  (skip: CLEWS dirs absent)"); return
    inc = signals.power_capex_increment(PHL.scenario.base_dir, PHL.scenario.reform_dir, PHL)
    assert len(inc) > 10 and np.isfinite(inc.values).all()
    cap = signals.read_clews_matrix(signals._find(PHL.scenario.reform_dir, "CapitalInvestment"))
    assert any(PHL.is_power(t) for t in cap.index)                 # power techs parsed


def test_report_transforms():
    b, r = _tpi(1.0), _tpi(1.0)
    r["C_i"] = r["C_i"] * 0.83                                     # ~ -17% energy demand
    dr = report.demand_response(b, r, I_E)
    assert abs(dr[0] - (-17.0)) < 0.5
    inc = report.incidence(b, r, I_E)
    assert inc["energy_by_J"].shape == (J,)


def test_commodity_shadow_price_dual():
    # MUIOGO exports the annual energy commodity-balance dual discounted to start-year PV
    # (raw * (1+DR)^(y-start+0.5)); the reader recovers the raw marginal and forms a ratio.
    import tempfile

    csv = ("r,f,y,EBb4_EnergyBalanceEachYear4_ICR,DiscountRate\n"
           "RE1,ELC,2020,1.520032676622447,0.05\n"   # = 1.4833681 * 1.05^0.5
           "RE1,ELC,2021,2.10,0.05\n"
           "RE1,GAS,2020,3.0,0.05\n")
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write(csv); path = f.name
    try:
        s = signals.commodity_shadow_price(path, fuel="ELC")              # undiscount by default
        assert abs(s.loc[2020] - 1.520032676622447 / (1.05 ** 0.5)) < 1e-6
        raw = signals.commodity_shadow_price(path, fuel="ELC", undiscount=False)
        assert abs(raw.loc[2020] - 1.520032676622447) < 1e-9
        default = signals.commodity_shadow_price(path)                    # default = ELC* prefix
        assert 2020 in default.index and 2021 in default.index
        ratio = signals.commodity_shadow_price_ratio(path, path, fuel="GAS")
        assert abs(ratio.loc[2020] - 1.0) < 1e-9                          # self-ratio is 1
    finally:
        os.remove(path)


def test_commodity_shadow_price_drops_slack_years():
    # A 0 (or sub-resolution near-zero) commodity-balance dual is a SLACK/unreported year -- missing
    # data, not a free price. Keeping it would let a reform-side zero form a ~100% collapse and a
    # base-side 1e-4 a ~10,000x spike. drop_zero (default) removes those so the ratio spans only
    # genuine-dual years and stays bounded. (Mirrors the real PHL_HOU_ELE pattern.)
    import tempfile

    # base: genuine dual in 2025/2041, slack-zero in 2030, sub-resolution 1e-4 in 2043
    base = ("r,f,y,EBb4_EnergyBalanceEachYear4_ICR,DiscountRate\n"
            "RE1,ELC,2025,8.0,0.0\nRE1,ELC,2030,0.0,0.0\n"
            "RE1,ELC,2041,4.0,0.0\nRE1,ELC,2043,0.0001,0.0\n")
    # reform: genuine in 2025/2041 (one moved), slack-zero in 2043, genuine in 2030
    ref = ("r,f,y,EBb4_EnergyBalanceEachYear4_ICR,DiscountRate\n"
           "RE1,ELC,2025,8.0,0.0\nRE1,ELC,2030,5.0,0.0\n"
           "RE1,ELC,2041,3.0,0.0\nRE1,ELC,2043,0.0,0.0\n")
    paths = []
    try:
        for txt in (base, ref):
            f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
            f.write(txt); f.close(); paths.append(f.name)
        bpath, rpath = paths
        s = signals.commodity_shadow_price(bpath, fuel="ELC")            # drop_zero default
        assert set(s.index) == {2025, 2041}                              # 2030 (zero) + 2043 (1e-4) dropped
        kept = signals.commodity_shadow_price(bpath, fuel="ELC", drop_zero=False)
        assert {2030, 2043} <= set(kept.index)                           # opt-out keeps them
        ratio = signals.commodity_shadow_price_ratio(bpath, rpath, fuel="ELC").dropna()
        assert set(ratio.index) == {2025, 2041}                          # only BOTH-genuine years
        assert abs(ratio.loc[2025] - 1.0) < 1e-9
        assert abs(ratio.loc[2041] - 0.75) < 1e-9                        # 3.0 / 4.0, bounded -- no spike
        assert (ratio < 100).all() and (ratio > 0).all()                 # no explosive / collapse artifact
    finally:
        for p in paths:
            os.remove(p)


def _write_cost_workbook(path, vals_by_year):
    """A minimal CLEWS 'Cost of electricity generation' workbook: a labeled cost ROW with integer
    year-column headers (the shape cost_of_electricity_ratio reads)."""
    import pandas as pd
    data = {"metric": ["Average electricity cost", "Total generation (PJ)"]}
    for y in sorted(vals_by_year):
        data[y] = [vals_by_year[y], 999.0]
    pd.DataFrame(data).to_excel(path, index=False)


def _write_lcoe_csvs(d, *, gen_inv, supply_vom, gen_out, busbar="ELC", fuel="COAL",
                     gen="GEN", mine="MINE"):
    """A minimal MUIOGO/OSeMOSYS export for the LCOE reader: one generation tech (``gen``, produces
    ``busbar`` and consumes ``fuel``) + one fuel supplier (``mine``, produces ``fuel``). Args are
    per-year dicts. LCOE = (gen own annualized capex + supplier var-O&M ALLOCATED to power by
    use-share) / busbar generation; with a single fuel user the share is 1, so numerator =
    gen_inv + supply_vom."""
    import pandas as pd
    ys = sorted(gen_out)

    def w(fname, rows):
        pd.DataFrame(rows).to_csv(os.path.join(d, fname), index=False)

    w("AnnualizedInvestmentCost.csv",
      [{"t": gen, "y": y, "AnnualizedInvestmentCost": gen_inv[y]} for y in ys])
    w("AnnualFixedOperatingCost.csv",
      [{"t": gen, "y": y, "AnnualFixedOperatingCost": 0.0} for y in ys])
    w("AnnualVariableOperatingCost.csv",
      [{"t": mine, "y": y, "AnnualVariableOperatingCost": supply_vom[y]} for y in ys])
    w("ProductionByTechnologyByMode.csv",
      [{"f": busbar, "t": gen, "y": y, "ProductionByTechnologyByMode": gen_out[y]} for y in ys] +
      [{"f": fuel, "t": mine, "y": y, "ProductionByTechnologyByMode": gen_out[y]} for y in ys])
    w("UseByTechnologyByMode.csv",
      [{"f": fuel, "t": gen, "y": y, "UseByTechnologyByMode": gen_out[y]} for y in ys])


def test_lcoe_ratio_from_csvs():
    # The workbook-less levelized source: numerator = generation own annualized capex + the upstream
    # fuel-supply cost ALLOCATED to power by use-share; denominator = busbar generation. This fixture
    # has one gen tech + one fuel supplier, so the fuel-allocation share is 1. Base LCOE = (100+100)/200
    # = 1.0; the reform RAISES capex (150) but CUTS fuel (90) -> (150+90)/200 = 1.2. The fuel term is
    # exactly what credits the reform's fuel savings against its higher capex (omitting it would report
    # 1.5, overstating the premium).
    import tempfile

    from oglink import lcoe
    b, r = tempfile.mkdtemp(), tempfile.mkdtemp()
    try:
        _write_lcoe_csvs(b, gen_inv={2026: 100., 2027: 100.}, supply_vom={2026: 100., 2027: 100.},
                         gen_out={2026: 200., 2027: 200.})
        _write_lcoe_csvs(r, gen_inv={2026: 150., 2027: 150.}, supply_vom={2026: 90., 2027: 90.},
                         gen_out={2026: 200., 2027: 200.})
        assert lcoe.lcoe_by_year(b, "ELC") == {2026: 1.0, 2027: 1.0}
        ratio = lcoe.lcoe_ratio(b, r, "ELC")
        assert abs(ratio.loc[2026] - 1.2) < 1e-9 and abs(ratio.loc[2027] - 1.2) < 1e-9
        # a supply_predicate that excludes the real fuel supplier must trip the completeness guard
        with __import__("pytest").raises(AssertionError, match="MATERIAL fuel producer"):
            lcoe.lcoe_by_year(r, "ELC", supply_predicate=lambda t: False)
    finally:
        for dd in (b, r):
            for f in os.listdir(dd):
                os.remove(os.path.join(dd, f))
            os.rmdir(dd)


def test_lcoe_find_tolerates_decoration_and_avoids_rate_collision():
    # region/year-decorated exports (RE1_<stem>_2050.csv) must resolve like the sibling readers glob,
    # WITHOUT grabbing a longer sibling that merely CONTAINS the stem (RateOfProductionByTechnologyByMode
    # -> the rate variable, not the level). Also exercises the pre-solve busbar-producer check.
    import tempfile

    from oglink import lcoe
    d = tempfile.mkdtemp()
    try:
        _write_lcoe_csvs(d, gen_inv={2026: 100.}, supply_vom={2026: 100.}, gen_out={2026: 200.})
        os.rename(os.path.join(d, "ProductionByTechnologyByMode.csv"),
                  os.path.join(d, "RE1_ProductionByTechnologyByMode_2050.csv"))
        with open(os.path.join(d, "RateOfProductionByTechnologyByMode.csv"), "w") as f:
            f.write("f,t,y,RateOfProductionByTechnologyByMode\nELC,GEN,2026,999\n")   # decoy
        found = lcoe._find(d, "ProductionByTechnologyByMode")
        assert found and os.path.basename(found) == "RE1_ProductionByTechnologyByMode_2050.csv"
        assert lcoe.has_inputs(d)                                    # glob-resolved presence check
        assert lcoe.has_busbar_producers(d, "ELC")                  # busbar names a real produced commodity
        assert not lcoe.has_busbar_producers(d, "NOPE")             # present-but-wrong busbar -> False (fail fast)
        assert lcoe.lcoe_by_year(d, "ELC") == {2026: 1.0}           # reader computes on the decorated name
    finally:
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
        os.rmdir(d)


def test_cost_of_electricity_ratio_reads_workbook():
    # The cost-index source (the curated workbook) is the REAL production path for a calibrated
    # country; exercise the reader + the fail-loud missing-row guard (no fixture existed before).
    import tempfile

    import pandas as pd
    d = tempfile.mkdtemp()
    try:
        bp = os.path.join(d, "base Cost of electricity generation.xlsx")
        rp = os.path.join(d, "reform Cost of electricity generation.xlsx")
        _write_cost_workbook(bp, {2026: 100.0, 2027: 100.0})
        _write_cost_workbook(rp, {2026: 110.0, 2027: 121.0})
        ratio = signals.cost_of_electricity_ratio(bp, rp)
        assert abs(ratio.loc[2026] - 1.10) < 1e-9 and abs(ratio.loc[2027] - 1.21) < 1e-9
        bad = os.path.join(d, "no-cost-row.xlsx")
        pd.DataFrame({"metric": ["Total generation (PJ)"], 2026: [1.0]}).to_excel(bad, index=False)
        raised = False
        try:
            signals.cost_of_electricity_ratio(bad, bad)
        except ValueError:
            raised = True
        assert raised, "a workbook with no 'average electricity cost' row must raise (fail loud)"
    finally:
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
        os.rmdir(d)


def test_energy_price_ratio_auto_selects_cost_index_with_workbook():
    # The other half of 'auto': when BOTH scenario dirs ship the cost-of-electricity workbook, 'auto'
    # must resolve to cost_index (not the dual) and equal an explicit kind='cost_index'.
    import tempfile

    bdir = tempfile.mkdtemp(); rdir = tempfile.mkdtemp()
    try:
        _write_cost_workbook(os.path.join(bdir, "Cost of electricity generation.xlsx"), {2026: 100.0, 2027: 100.0})
        _write_cost_workbook(os.path.join(rdir, "Cost of electricity generation.xlsx"), {2026: 110.0, 2027: 121.0})
        assert signals._has_cost_xlsx(bdir) and signals._has_cost_xlsx(rdir)
        kw = dict(base_dir=bdir, reform_dir=rdir, share=0.5, og_start_year=2026, n=2, fuel="ELC")
        auto = signals.energy_price_ratio("auto", **kw)
        ci = signals.energy_price_ratio("cost_index", **kw)
        assert auto is not None and np.allclose(auto, ci)            # auto -> cost_index when workbook present
        assert np.allclose(auto, [1.05, 1.105])                      # 1 + 0.5*(ratio-1); ratio = 1.10, 1.21
    finally:
        for d in (bdir, rdir):
            for f in os.listdir(d):
                os.remove(os.path.join(d, f))
            os.rmdir(d)


def test_energy_price_rejects_nonpositive_ratio():
    # A degenerate aligned ratio (all-zero -- e.g. an all-slack dual or a horizon ending before
    # og_start_year) would make r*(1+tau)-1 = -1: a silent -100% consumption wedge. The channel must
    # FAIL LOUD and mutate nothing, not apply it.
    ctx = _ctx()
    before = np.array(ctx.og_reform.tau_c)
    raised = False
    try:
        channels.energy_price(ctx, price_ratio=np.zeros(TS))
    except ValueError:
        raised = True
    assert raised, "all-zero price ratio must raise (it would invert the wedge to -100%)"
    assert np.allclose(ctx.og_reform.tau_c, before)                  # nothing mutated on the raise


def test_energy_price_skips_when_ratio_none():
    # share is None (country can't isolate electricity's value-share) -> energy_price_ratio returns None
    # -> the channel must skip cleanly (record + no mutation), the documented contract.
    ctx = _ctx()
    before = np.array(ctx.og_reform.tau_c)
    rec = channels.energy_price(ctx, price_ratio=None)
    assert rec.get("skipped") is True
    assert np.allclose(ctx.og_reform.tau_c, before)


def test_energy_price_tfp_lowers_electricity_Z():
    # Option A: a +20% electricity price via the industry's TFP -> Z[:, e] /= 1.20 (p_m ~ 1/Z), other
    # industries untouched. No solve: this is the pre-solve Z mutation the channel performs.
    ctx = _ctx()
    base_Z = np.array(ctx.og_reform.Z)
    rec = channels.energy_price_tfp(ctx, price_ratio=1.20)
    Z = np.asarray(ctx.og_reform.Z)
    assert np.allclose(Z[:, M_E], base_Z[:, M_E] / 1.20)
    assert all(np.allclose(Z[:, m], base_Z[:, m]) for m in range(M) if m != M_E)
    assert abs(rec["z_multiplier_0"] - 1 / 1.20) < 1e-9 and rec["industry_index"] == M_E


def test_energy_price_tfp_skips_without_industry():
    con = Concordance(energy_industry_index=None, energy_good_index=I_E)
    ctx = ExperimentContext(country=PHL, concordance=con, og_reform=_params(), base_tpi=_tpi(1.0))
    base_Z = np.array(ctx.og_reform.Z)
    rec = channels.energy_price_tfp(ctx, price_ratio=1.20)
    assert rec.get("skipped") is True
    assert np.allclose(ctx.og_reform.Z, base_Z)


def test_energy_price_tfp_rejects_nonpositive():
    ctx = _ctx()
    base_Z = np.array(ctx.og_reform.Z)
    raised = False
    try:
        channels.energy_price_tfp(ctx, price_ratio=0.0)
    except ValueError:
        raised = True
    assert raised, "a zero price ratio would make Z non-positive (negative TFP)"
    assert np.allclose(ctx.og_reform.Z, base_Z)


def test_energy_cost_push_haircuts_by_intensity():
    # Option A': a +20% electricity price as a per-industry cost-push, weighted by electricity's input
    # share phi_j -> Z[:, j] /= (1 + phi_j*0.20). Industries with phi_j=0 are untouched.
    ctx = _ctx()
    base_Z = np.array(ctx.og_reform.Z)
    phi = np.zeros(M); phi[M_E] = 0.3; phi[2] = 0.1     # electricity-using industries
    rec = channels.energy_cost_push(ctx, price_ratio=1.20, electricity_intensity=phi)
    Z = np.asarray(ctx.og_reform.Z)
    for m in range(M):
        assert np.allclose(Z[:, m], base_Z[:, m] / (1.0 + phi[m] * 0.20)), m
    assert rec["n_industries_hit"] == 2 and abs(rec["max_haircut_0"] - (1 - 1 / 1.06)) < 1e-9


def test_energy_cost_push_skips_without_intensity():
    ctx = _ctx()
    base_Z = np.array(ctx.og_reform.Z)
    rec = channels.energy_cost_push(ctx, price_ratio=1.20, electricity_intensity=None)
    assert rec.get("skipped") is True
    assert np.allclose(ctx.og_reform.Z, base_Z)


def test_energy_cost_push_shape_guard():
    ctx = _ctx()
    raised = False
    try:
        channels.energy_cost_push(ctx, price_ratio=1.20, electricity_intensity=np.zeros(M + 1))
    except ValueError:
        raised = True
    assert raised, "a phi vector that does not align to M must raise"


def test_input_intensity_from_sam():
    # electricity's input-cost share per industry, from a minimal SAM: manufacturing buys 20 of
    # electricity against a gross output of 50 -> phi=0.4; electricity self-uses 5 of 15 -> 0.333.
    import pandas as pd

    from oglink import aggregation
    idx = ["celec", "cmanu", "aelec", "amanu"]
    sam = pd.DataFrame(0.0, index=idx, columns=idx)
    sam.loc["celec", "aelec"] = 5.0;  sam.loc["cmanu", "aelec"] = 10.0    # electricity activity inputs
    sam.loc["celec", "amanu"] = 20.0; sam.loc["cmanu", "amanu"] = 30.0    # manufacturing inputs
    prod = {"Electricity": ["aelec"], "Manufacturing": ["amanu"]}
    phi = aggregation.input_intensity(sam, prod)
    assert np.allclose(phi, [5.0 / 15.0, 20.0 / 50.0])


def test_Z_is_mutable_in_override_diff():
    # the foundation: a Z change must now appear in the cross-env override diff (it was read-only before).
    from oglink import serde
    assert "Z" in serde.MUTABLE_PARAM_KEYS
    p = _params()
    base = {k: np.array(getattr(p, k), dtype=float) for k in serde.MUTABLE_PARAM_KEYS}
    assert "Z" not in serde.diff_against_baseline(p, base)        # unchanged -> not in the diff
    p.Z = np.asarray(p.Z, dtype=float) * 0.9                      # a channel lowers TFP
    assert "Z" in serde.diff_against_baseline(p, base)            # now carried across the boundary


def test_energy_full_composes_costpush_and_wedge():
    # The composite experiment must (a) cost-push every USING industry by phi_j, (b) ZERO electricity's
    # own self-use (so it doesn't double-count the wedge), and (c) raise the energy good's consumption
    # wedge by electricity's value-share of it. Stub the SAM-read intensity so no package/SAM is needed.
    from oglink import experiments
    ctx = _ctx()
    base_Z = np.array(ctx.og_reform.Z); base_tau = np.array(ctx.og_reform.tau_c)
    phi = np.full(M, 0.1); phi[M_E] = 0.5                 # electricity self-use 0.5 must be zeroed
    orig = experiments._electricity_intensity
    experiments._electricity_intensity = lambda c: phi
    try:
        experiments.energy_full(ctx, solve=lambda c: None)
    finally:
        experiments._electricity_intensity = orig
    Z = np.asarray(ctx.og_reform.Z); tau = np.asarray(ctx.og_reform.tau_c)
    assert np.allclose(Z[:, M_E], base_Z[:, M_E])         # electricity's own Z NOT haircut (self-use zeroed)
    other = next(m for m in range(M) if m != M_E)
    assert np.allclose(Z[:, other], base_Z[:, other] / (1 + 0.1 * 0.20))   # a using industry IS hit
    share = float(np.asarray(ctx.og_reform.io_matrix)[I_E, M_E])
    assert abs((1 + tau[0, I_E]) - (1 + share * 0.20) * (1 + base_tau[0, I_E])) < 1e-9   # final wedge
    assert all(np.allclose(tau[:, i], base_tau[:, i]) for i in range(I) if i != I_E)     # only energy good


def _ctx_at(mi, gi):
    """A ctx whose concordance pins the energy industry/good at arbitrary indices (to prove the channel
    math is index-driven, not fixed at the fixture's 1)."""
    return ExperimentContext(country=PHL, concordance=Concordance(energy_industry_index=mi, energy_good_index=gi),
                             og_reform=_params(), base_tpi=_tpi(1.0))


def test_energy_channels_route_at_nonunit_index():
    # index-INDEPENDENCE at the channel/composite layer: run at energy index 2 (PHL-real shape, not the
    # fixture default 1) and assert the Z mutation + self-use-zeroing land on column 2, nothing else.
    ctx = _ctx_at(2, 2)
    base_Z = np.array(ctx.og_reform.Z)
    channels.energy_price_tfp(ctx, price_ratio=1.20)
    Z = np.asarray(ctx.og_reform.Z)
    assert np.allclose(Z[:, 2], base_Z[:, 2] / 1.20)
    assert all(np.allclose(Z[:, m], base_Z[:, m]) for m in range(M) if m != 2)
    ctx2 = _ctx_at(2, 2); bZ = np.array(ctx2.og_reform.Z); btau = np.array(ctx2.og_reform.tau_c)
    phi = np.full(M, 0.1); phi[2] = 0.5
    orig = experiments._electricity_intensity
    experiments._electricity_intensity = lambda c: phi
    try:
        experiments.energy_full(ctx2, solve=lambda c: None)
    finally:
        experiments._electricity_intensity = orig
    Z2 = np.asarray(ctx2.og_reform.Z); tau2 = np.asarray(ctx2.og_reform.tau_c)
    assert np.allclose(Z2[:, 2], bZ[:, 2])                       # electricity self-use zeroed at index 2
    assert np.allclose(Z2[:, 0], bZ[:, 0] / (1 + 0.1 * 0.20))    # a using industry IS hit
    assert tau2[0, 2] > btau[0, 2] and np.allclose(tau2[:, 0], btau[:, 0])   # wedge on good index 2 only


def test_energy_full_skips_when_not_couplable():
    # the composite is the couplable headline: no concordance, or no energy_industry/good index -> skip
    # both legs cleanly (no crash, no mutation). Covers single-industry / fused-electricity countries.
    for con in (None,
                Concordance(energy_industry_index=None, energy_good_index=I_E),
                Concordance(energy_industry_index=M_E, energy_good_index=None)):
        ctx = ExperimentContext(country=PHL, concordance=con, og_reform=_params(), base_tpi=_tpi(1.0))
        bZ = np.array(ctx.og_reform.Z); btau = np.array(ctx.og_reform.tau_c)
        experiments.energy_full(ctx, solve=lambda c: None)       # must not call the SAM or mutate anything
        assert np.allclose(ctx.og_reform.Z, bZ) and np.allclose(ctx.og_reform.tau_c, btau)


def test_energy_full_wedge_only_when_no_sam():
    # couplable country but the package ships no SAM -> _electricity_intensity None -> cost-push leg skips,
    # but the (concordance-resolved) final wedge still fires.
    ctx = _ctx()
    bZ = np.array(ctx.og_reform.Z); btau = np.array(ctx.og_reform.tau_c)
    orig = experiments._electricity_intensity
    experiments._electricity_intensity = lambda c: None
    try:
        experiments.energy_full(ctx, solve=lambda c: None)
    finally:
        experiments._electricity_intensity = orig
    assert np.allclose(ctx.og_reform.Z, bZ)                      # cost-push skipped (no intensity)
    share = float(np.asarray(ctx.og_reform.io_matrix)[I_E, M_E])
    tau = np.asarray(ctx.og_reform.tau_c)
    assert abs((1 + tau[0, I_E]) - (1 + share * 0.20) * (1 + btau[0, I_E])) < 1e-9   # wedge fired


def test_energy_cost_push_rejects_nonpositive_and_collapsing():
    # symmetric guards: a non-positive ratio, and a price DROP big enough that 1+phi*(r-1)<=0, both raise
    # and mutate nothing.
    ctx = _ctx(); bZ = np.array(ctx.og_reform.Z)
    for pr, phi in ((0.0, np.full(M, 0.1)), (0.1, _collapsing_phi())):
        raised = False
        try:
            channels.energy_cost_push(ctx, price_ratio=pr, electricity_intensity=phi)
        except ValueError:
            raised = True
        assert raised, (pr, phi)
        assert np.allclose(ctx.og_reform.Z, bZ)


def _collapsing_phi():
    phi = np.zeros(M); phi[M_E] = 2.0    # 1 + 2.0*(0.1-1) = -0.8 <= 0
    return phi


def test_input_intensity_branches():
    # carrier as a list of codes; the 'no commodity-rows -> fall back to any match' branch; and an
    # industry the SAM lacks output for (phi=0).
    import pandas as pd

    from oglink import aggregation
    idx = ["celec", "cmanu", "aelec", "amanu"]
    sam = pd.DataFrame(0.0, index=idx, columns=idx)
    sam.loc["celec", "amanu"] = 20.0; sam.loc["cmanu", "amanu"] = 30.0
    sam.loc["celec", "aelec"] = 5.0;  sam.loc["cmanu", "aelec"] = 10.0
    phi_list = aggregation.input_intensity(sam, {"Elec": ["aelec"], "Mfg": ["amanu"]}, carrier=["celec"])
    assert np.allclose(phi_list, [5.0 / 15.0, 20.0 / 50.0])      # list-of-codes carrier
    phi_ghost = aggregation.input_intensity(sam, {"Elec": ["aelec"], "Ghost": ["aghost"]})
    assert phi_ghost[1] == 0.0                                   # industry with no SAM output -> 0
    sam2 = pd.DataFrame(0.0, index=["aelec", "amanu"], columns=["aelec", "amanu"])
    sam2.loc["aelec", "amanu"] = 4.0                             # only activity rows (no 'c*' commodity rows)
    phi_fallback = aggregation.input_intensity(sam2, {"Mfg": ["amanu"]})
    assert phi_fallback[0] == 1.0                                # crows falls back to the carrier match


def test_electricity_intensity_reads_sam_via_registry():
    # exercise the REAL _electricity_intensity body (registry -> SAM -> input_intensity), which the
    # composite test stubs out; and the wrong-length -> None degrade.
    import pandas as pd

    from oglink import discovery, registry
    sam = pd.DataFrame(0.0, index=["celec", "cmanu", "aelec", "amanu", "aagr", "asrv"],
                       columns=["celec", "cmanu", "aelec", "amanu", "aagr", "asrv"])
    sam.loc["celec", "amanu"] = 20.0; sam.loc["cmanu", "amanu"] = 30.0
    prod4 = {"Elec": ["aelec"], "Mfg": ["amanu"], "Agr": ["aagr"], "Srv": ["asrv"]}   # M=4 == fixture
    ctx = _ctx()
    saved = (registry.lookup, registry.package_source_dir, discovery._read_sam, discovery.read_package_dicts)
    registry.lookup = lambda *a, **k: object()
    registry.package_source_dir = lambda e: "/nonexistent"
    discovery._read_sam = lambda src: sam
    discovery.read_package_dicts = lambda src: (prod4, None)
    try:
        phi = experiments._electricity_intensity(ctx)
        assert phi is not None and phi.shape == (4,) and abs(phi[1] - 20.0 / 50.0) < 1e-9
        discovery.read_package_dicts = lambda src: ({"A": ["aelec"], "B": ["amanu"]}, None)  # M=2 != 4
        assert experiments._electricity_intensity(ctx) is None    # wrong length -> None, not a raise
    finally:
        registry.lookup, registry.package_source_dir, discovery._read_sam, discovery.read_package_dicts = saved


def test_transmissions_touch_disjoint_state():
    # the Z modes must not touch tau_c, and the tau_c wedge must not touch Z (guards against an accidental
    # cross-mutation regression that the composite relies on).
    ctx = _ctx(); btau = np.array(ctx.og_reform.tau_c)
    channels.energy_price_tfp(ctx, price_ratio=1.20)
    assert np.allclose(ctx.og_reform.tau_c, btau)
    ctx2 = _ctx(); btau2 = np.array(ctx2.og_reform.tau_c)
    channels.energy_cost_push(ctx2, price_ratio=1.20, electricity_intensity=np.full(M, 0.1))
    assert np.allclose(ctx2.og_reform.tau_c, btau2)
    ctx3 = _ctx(); bZ3 = np.array(ctx3.og_reform.Z)
    channels.energy_price(ctx3, price_ratio=1.20)
    assert np.allclose(ctx3.og_reform.Z, bZ3)


def test_energy_price_ratio_auto_prefers_lcoe_never_marginal():
    # 'auto' policy: workbook -> lcoe -> NEVER the marginal. With no workbook but the LCOE CSVs + a
    # busbar code, 'auto' resolves to 'lcoe' (dense/smooth) and equals an explicit kind='lcoe'. With
    # ONLY the EBb4 marginal export (no workbook, no LCOE inputs, no busbar), 'auto' must RAISE loudly:
    # it never silently falls to the degenerate marginal (which would broadcast a single binding year).
    import tempfile

    import pytest
    b, r = tempfile.mkdtemp(), tempfile.mkdtemp()
    try:
        _write_lcoe_csvs(b, gen_inv={2026: 100., 2027: 100.}, supply_vom={2026: 100., 2027: 100.},
                         gen_out={2026: 200., 2027: 200.})
        _write_lcoe_csvs(r, gen_inv={2026: 150., 2027: 150.}, supply_vom={2026: 90., 2027: 90.},
                         gen_out={2026: 200., 2027: 200.})
        kw = dict(base_dir=b, reform_dir=r, share=0.5, og_start_year=2026, n=2, busbar="ELC")
        resolved = {}
        auto = signals.energy_price_ratio("auto", resolved=resolved, **kw)
        lc = signals.energy_price_ratio("lcoe", **kw)
        assert resolved["requested"] == "auto" and resolved["kind"] == "lcoe"
        assert np.allclose(auto, lc) and np.allclose(auto, [1.10, 1.10])   # 1 + 0.5*(1.2-1)

        # only the EBb4 marginal present (no workbook / no LCOE inputs / no busbar) -> auto refuses
        eb = tempfile.mkdtemp()
        with open(os.path.join(eb, "EBb4_EnergyBalanceEachYear4_ICR.csv"), "w") as f:
            f.write("r,f,y,EBb4_EnergyBalanceEachYear4_ICR,DiscountRate\nRE1,ELC,2026,2.0,0.0\n")
        try:
            with pytest.raises(ValueError, match="no levelized price source"):
                signals.energy_price_ratio("auto", base_dir=eb, reform_dir=eb, share=0.5,
                                           og_start_year=2026, n=2, fuel="ELC")
        finally:
            os.remove(os.path.join(eb, "EBb4_EnergyBalanceEachYear4_ICR.csv"))
            os.rmdir(eb)
    finally:
        for dd in (b, r):
            for f in os.listdir(dd):
                os.remove(os.path.join(dd, f))
            os.rmdir(dd)


def test_energy_price_marginal_source():
    # kind='marginal' drives the energy wedge from the commodity-balance shadow-price RATIO (not the
    # controlled shock). Stub the reader so the branch + guardrail + alignment are exercised with no
    # CLEWS files and no OG solve. Three overlapping years clear the sparse-marginal guardrail.
    import pandas as pd

    ctx = _ctx()
    sy = PHL.scenario.og_start_year
    share = float(np.asarray(ctx.og_reform.io_matrix)[I_E, M_E])      # electricity's share of the energy good
    n = np.asarray(ctx.og_reform.tau_c).shape[0]
    orig = signals.commodity_shadow_price_ratio
    signals.commodity_shadow_price_ratio = lambda b, r, **k: pd.Series([1.20, 1.20, 1.20],
                                                                       index=[sy, sy + 1, sy + 2])
    try:
        # sourcing (dispatch + dilution + align) now lives in signals.energy_price_ratio; the channel
        # just applies the ready good-level ratio.
        ratio = signals.energy_price_ratio("marginal", base_dir=PHL.scenario.base_dir,
                                           reform_dir=PHL.scenario.reform_dir, share=share,
                                           og_start_year=sy, n=n)
        channels.energy_price(ctx, price_ratio=ratio)
    finally:
        signals.commodity_shadow_price_ratio = orig
    tau = np.asarray(ctx.og_reform.tau_c)[0, I_E]
    # electricity marginal ratio is diluted by `share` into the broader energy good, then folded into (1+tau)
    assert abs((1 + tau) - (1 + share * 0.20) * 1.12) < 1e-9, tau


def test_energy_price_marginal_guardrail_rejects_sparse_overlap():
    # the marginal is degenerate: if base/reform overlap in fewer than the minimum years, refuse rather
    # than let _align_to_start broadcast a single binding year into a permanent shock.
    import pandas as pd
    import pytest
    orig = signals.commodity_shadow_price_ratio
    signals.commodity_shadow_price_ratio = lambda b, r, **k: pd.Series([1.32], index=[2029])
    try:
        with pytest.raises(ValueError, match="overlaps in only 1 year"):
            signals.energy_price_ratio("marginal", base_dir="x", reform_dir="y", share=1.0,
                                       og_start_year=2026, n=10, fuel="ELC")
    finally:
        signals.commodity_shadow_price_ratio = orig


def test_muiogo_run_reader():
    from oglink import muiogo_run

    if not os.path.isdir(_MUIOGO_RUN):
        print("  (skip: MUIOGO sample run absent)"); return
    csv_dir = muiogo_run.find_run_csv_dir(_MUIOGO_RUN)
    assert os.path.basename(csv_dir) == "csv"
    fuels = muiogo_run.electricity_fuels(csv_dir)
    assert fuels and all(f.upper().startswith("ELC") for f in fuels)   # ELC001/ELC002
    assert muiogo_run.verify_run(csv_dir)[muiogo_run._EBB4] is True
    s = signals.commodity_shadow_price(csv_dir, fuel=fuels[0])         # reader consumes the run dir
    assert len(s) > 0 and np.isfinite(s.values).all()


def test_run_manifest():
    import json
    import tempfile

    from oglink import experiments
    from oglink.manifest import write_run_manifest

    ctx = _ctx()
    ctx.log("energy_price", source="controlled_+20%", dtau_mean=0.224)
    exp = experiments.get("energy_price")
    with tempfile.TemporaryDirectory() as d:
        path = write_run_manifest(d, exp, PHL, ctx, clews_run="/some/muiogo/run")
        m = json.load(open(path))
    assert m["experiment"]["name"] == "energy_price"
    assert m["country"] == "Philippines"
    assert m["scenario"]["name"] == "PEP_vs_Base"
    assert m["clews_run"] == "/some/muiogo/run"
    assert m["channels"][0]["id"] == "energy_price" and len(m["provenance"]) == 1


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
            passed += 1
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
