"""Link-side unit tests for the cross-env serialization. numpy-only, no ogcore. Includes the duck-type
CONTRACT test: a real channel mutates an OGParams exactly as it would a Specifications. Run with the
standalone link venv: `uv run pytest tests/test_serde.py`.
"""
from __future__ import annotations

import numpy as np

from oglink import serde


def test_ogparams_get_set_and_update_stub():
    p = serde.OGParams(T=20, tau_c=np.zeros((28, 5)))
    p.tau_c[0, 1] = 0.3
    assert p.tau_c[0, 1] == 0.3
    p.update_specifications({"gamma": np.full(4, 0.5)})        # stub: just sets attrs
    assert p.gamma[0] == 0.5


def test_diff_is_sparse(tmp_path):
    base = {"tau_c": np.full((28, 5), 0.12), "gamma": np.full(4, 0.5),
            "alpha_I": np.full(28, 0.02), "e": np.ones((20, 8, 7))}
    og = serde.OGParams(**{k: v.copy() for k, v in base.items()})
    og.tau_c[:, 1] = 0.20                                       # mutate ONLY tau_c
    diff = serde.diff_against_baseline(og, base)
    assert set(diff) == {"tau_c"}                               # only the changed array is emitted
    assert isinstance(diff["tau_c"], list)                      # JSON-ready nested list


def test_overrides_json_roundtrip(tmp_path):
    diff = {"tau_c": np.full((3, 2), 0.2).tolist(), "gamma": [0.6, 0.5]}
    path = tmp_path / "ov.json"
    serde.write_overrides_json(diff, path)
    back = serde.read_overrides_json(path)                      # runner-side: lists -> float64 arrays
    assert isinstance(back["tau_c"], np.ndarray) and back["tau_c"].dtype == float
    assert np.allclose(back["gamma"], [0.6, 0.5])


def test_health_json_shape(tmp_path):
    shock = {"excess_deaths": -279.0, "profile": np.linspace(0, 1, 100), "phase_years": 5, "rc_ss": 1e-5}
    path = tmp_path / "h.json"
    serde.write_health_json(shock, path)
    back = serde.read_health_json(path)
    assert back["excess_deaths"] == -279.0 and back["phase_years"] == 5 and back["rc_ss"] == 1e-5
    assert isinstance(back["profile"], np.ndarray) and len(back["profile"]) == 100


def test_solution_npz_roundtrip_no_pickle(tmp_path):
    sol = {"C_i": np.full((20, 5), 10.0), "Y": np.full(20, 100.0), "r_p": np.full(20, 0.05)}
    path = str(tmp_path / "sol.npz")
    serde.save_solution_npz(path, sol)
    back = serde.load_solution(path)                            # np.load(allow_pickle=False)
    assert set(back) == {"C_i", "Y", "r_p"} and np.allclose(back["Y"], 100.0)


def test_solution_npz_rejects_object_dtype(tmp_path):
    import pytest
    with pytest.raises(TypeError):
        serde.save_solution_npz(str(tmp_path / "bad.npz"), {"C_i": np.array([[1, 2], [3]], dtype=object)})


def test_duck_type_contract_real_channel():
    # the load-bearing guard: a REAL channel must mutate an OGParams exactly as a Specifications would,
    # with NO ogcore present. If a channel ever calls a Specifications method, this fails fast here
    # (in the fast link suite) rather than only in a cross-env solve.
    from oglink import channels
    from oglink.contract import Concordance
    from oglink.country import PHL
    from oglink.framework import ExperimentContext

    T, S, J, M, I = 20, 8, 7, 4, 5
    TS = T + S
    i_e = 1                                  # energy good index; the concordance is per-run, so pin one
    base = {"tau_c": np.full((TS, I), 0.12), "c_min": np.zeros(I), "alpha_T": np.full(TS, 0.05),
            "e": np.ones((T, S, J))}
    og = serde.OGParams(T=T, M=M, I=I, E=0, S=S, **{k: v.copy() for k, v in base.items()})
    ctx = ExperimentContext(country=PHL, concordance=Concordance(energy_industry_index=1, energy_good_index=i_e),
                            og_reform=og, base_tpi=None)
    channels.energy_price(ctx, price_ratio=1.20)                # plain attribute writes -> mutates og.tau_c
    assert abs((1 + og.tau_c[0, i_e]) - 1.20 * 1.12) < 1e-9
    diff = serde.diff_against_baseline(og, base)
    assert "tau_c" in diff                                      # the link would ship exactly this override
