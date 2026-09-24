"""The acceptance gate (slow, opt-in): the ported `coupled` forward pass reproduces the committed golden
Y_ss on PHL v9. Requires a registered OG-PHL env + the CLEWS base/reform run dirs, so it SKIPS cleanly
when they are absent. Run with:  pytest -m slow  (after registering an OG model + setting the CLEWS dirs).

The gate value is the reference golden `coupled` Y_ss = -0.13847519...%. This test is the definition of
PR-1 "done"; it is not exercised by the default unit run.
"""
import os

import pytest

pytestmark = pytest.mark.slow

GOLDEN_COUPLED_Y_SS = -0.13847519360527663   # the committed golden `coupled` steady-state output effect
TOL = 5e-3                                    # 0.005 percentage-point band around the golden


def _phl_ready():
    """(country, registry-ok) only if an OG-PHL is resolvable and both CLEWS dirs exist -- else skip."""
    try:
        from oglink import registry
        from oglink.country import resolve_country
        c = resolve_country("phl")
        registry.lookup(c)                    # raises if no OG-PHL env is registered/on disk
    except Exception as e:                     # noqa: BLE001 -- any resolution failure -> skip, don't fail
        return None, f"OG-PHL not registered: {type(e).__name__}"
    b, r = c.scenario.base_dir, c.scenario.reform_dir
    if not (b and r and os.path.isdir(b) and os.path.isdir(r)):
        return None, "CLEWS base/reform scenario dirs unset or missing"
    return c, None


def test_coupled_reproduces_golden_y_ss():
    country, why = _phl_ready()
    if country is None:
        pytest.skip(why)
    from functools import partial

    from oglink import experiments, framework, golden, runtime
    cfg = runtime.RunnerConfig(num_workers=7, show_progress=False)
    ctx = framework.run(
        experiments.coupled, country,
        export_baseline=partial(runtime.export_baseline, cfg=cfg),
        solve_reform=partial(runtime.solve_reform, cfg=cfg),
        out_root="./_pr1_gate_run")
    rec = golden.from_context("coupled", ctx)
    y_ss = rec["pct_diff"]["Y_ss"]
    assert abs(y_ss - GOLDEN_COUPLED_Y_SS) < TOL, f"Y_ss {y_ss} off golden {GOLDEN_COUPLED_Y_SS}"
