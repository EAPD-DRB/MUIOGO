"""Link-side transforms on synthetic fixtures -- pure numpy, no ogcore, no solve.

Covers the wedge math (og_wedge), the macro read-out (report), and the cross-env override diff (serde):
the numeric core of the forward pass, tested without touching the OG model.
"""
import json
import types

import numpy as np

from oglink import og_wedge, report, serde


def test_effective_price_to_tau_c():
    # (1 + tau_new) = ratio * (1 + tau_base); a +10% price on a zero base is tau=0.10
    assert np.isclose(og_wedge.effective_price_to_tau_c(1.10, 0.0), 0.10)
    assert np.isclose(og_wedge.effective_price_to_tau_c(1.10, 0.05), 1.10 * 1.05 - 1.0)


def test_set_energy_consumption_wedge_only_touches_energy_good():
    p = types.SimpleNamespace(tau_c=np.zeros((3, 2)))
    out, diag = og_wedge.set_energy_consumption_wedge(p, i_energy=1, price_ratio_by_t=1.20)
    assert np.allclose(out.tau_c[:, 1], 0.20)      # energy good wedged by +20%
    assert np.allclose(out.tau_c[:, 0], 0.0)       # the other good untouched
    assert diag["i_energy"] == 1


def test_energy_demand_response_pct():
    base = np.full((4, 2), 100.0)
    reform = base.copy()
    reform[:, 1] = 90.0
    resp = og_wedge.energy_demand_response(base, reform, i_energy=1)
    assert np.allclose(resp, -10.0)


def test_macro_table_ss_pct():
    base = {"Y": np.full(12, 100.0), "C": np.full(12, 50.0)}
    reform = {"Y": base["Y"].copy(), "C": base["C"].copy()}
    reform["Y"][-1] = 99.0        # -1% at the steady state
    df = report.macro_table(base, reform, start_year=2026)
    assert np.isclose(df.loc["SS", "Y"], -1.0)
    assert np.isclose(df.loc["SS", "C"], 0.0)


def test_serde_diff_is_sparse_and_roundtrips(tmp_path):
    baseline = {"tau_c": np.zeros((2, 2)), "Z": np.ones((2, 2))}
    reform = serde.OGParams(tau_c=np.array([[0.0, 0.2], [0.0, 0.2]]), Z=np.ones((2, 2)))
    diff = serde.diff_against_baseline(reform, baseline)
    assert set(diff) == {"tau_c"}                  # Z unchanged -> excluded (sparse)
    p = tmp_path / "ov.json"
    serde.write_overrides_json(diff, p)
    back = serde.read_overrides_json(p)
    assert np.allclose(back["tau_c"], reform.tau_c)
    # the JSON is plain (dtype lost then recast) -- confirm it is valid JSON, not a pickle
    assert "tau_c" in json.loads(p.read_text())


def test_ogparams_update_specifications():
    p = serde.OGParams(a=1)
    p.update_specifications({"a": 2, "b": 3})
    assert p.a == 2 and p.b == 3
