"""Unit tests for oglink.golden — the test-battery golden-record capture/compare.
Synthetic SS/TPI result dicts; no model solves."""
import numpy as np
import pytest

from oglink import golden


def test_aggregates_ss_scalars():
    ss = {"Y": 2.0, "C": 1.5, "K": 5.0, "L": 1.0, "r": 0.05, "w": 1.2, "Y_m": [0.5, 0.3, 0.7, 0.5]}
    a = golden.aggregates(ss)
    assert a["Y"] == 2.0 and a["r"] == 0.05
    assert a["Y_m"] == [0.5, 0.3, 0.7, 0.5]


def test_aggregates_tpi_arrays():
    T = 30
    series = np.linspace(1.0, 2.0, T)
    tpi = {"Y": series, "Y_m": np.ones((T, 3)) * np.array([1.0, 2.0, 3.0])}
    a = golden.aggregates(tpi)
    assert a["Y_t0"] == pytest.approx(1.0)
    assert a["Y_ss"] == pytest.approx(2.0)
    assert a["Y_t10"] == pytest.approx(series[10])
    assert a["Y_m"] == [1.0, 2.0, 3.0]            # SS/last TPI row


def test_capture_pct_diff():
    rec = golden.capture("t", {"Y": 2.0, "C": 1.0}, {"Y": 2.1, "C": 0.9})
    assert rec["run"] == "t"
    assert rec["pct_diff"]["Y"] == pytest.approx(5.0)
    assert rec["pct_diff"]["C"] == pytest.approx(-10.0)


def test_capture_base_only_has_no_pct():
    rec = golden.capture("b", {"Y": 2.0})
    assert "reform" not in rec and "pct_diff" not in rec


def test_save_load_roundtrip(tmp_path):
    p = str(tmp_path / "golden.json")
    golden.save(golden.capture("run1", {"Y": 2.0}, {"Y": 2.1}), p)
    golden.save(golden.capture("run2", {"Y": 3.0}), p)
    table = golden.load(p)
    assert set(table) == {"run1", "run2"}
    assert table["run1"]["pct_diff"]["Y"] == pytest.approx(5.0)


def test_compare_match_and_diff():
    rec = golden.capture("t", {"Y": 2.0}, {"Y": 2.1})
    assert golden.compare(rec, rec)["match"] is True
    drifted = golden.capture("t", {"Y": 2.0}, {"Y": 2.2})
    cmp = golden.compare(drifted, rec)
    assert cmp["match"] is False and "reform.Y" in cmp["diffs"]


def test_check_no_golden_then_established_then_drift(tmp_path):
    p = str(tmp_path / "golden.json")
    r = golden.check("t", {"Y": 2.0}, {"Y": 2.1}, path=p)
    assert r["had_golden"] is False and r["match"] is None      # no baseline yet
    golden.save(r["record"], p)                                  # establish it
    assert golden.check("t", {"Y": 2.0}, {"Y": 2.1}, path=p)["match"] is True
    assert golden.check("t", {"Y": 2.0}, {"Y": 2.5}, path=p)["match"] is False


def test_from_context():
    ctx = type("Ctx", (), {})()
    ctx.base_tpi, ctx.reform_tpi = {"Y": 2.0}, {"Y": 2.1}
    rec = golden.from_context("fc", ctx)
    assert rec["pct_diff"]["Y"] == pytest.approx(5.0)
