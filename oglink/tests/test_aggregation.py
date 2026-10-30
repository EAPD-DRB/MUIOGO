"""Tests for oglink.aggregation -- the generic sub-good shock targeter.

Two layers:
  * synthetic fixtures (deterministic, always run) -- prove the share/weight/warning logic
    is country-agnostic, driven only by the dict + SAM passed in;
  * local-integration (skipped if the sibling OG repos aren't present) -- prove it reads the
    REAL PROD_DICT/CONS_DICT + SAM of PHL/IDN/ZAF/ETH and reproduces the hand-checked shares.
"""
import ast
import glob
import os

import numpy as np
import pandas as pd
import pytest

from oglink import aggregation as ag


# --- synthetic SAM: known column (gross output) and row (absorption) totals -----------------
# activity gross output (column sum over commodity/va rows): a_e=100, a_w=20, a_x=80
# commodity absorption (row sum over activity + hh cols):    c_e=20,  c_w=10, c_x=50
@pytest.fixture
def sam():
    idx = ["c_e", "c_w", "c_x", "va", "total"]
    cols = ["desc", "a_e", "a_w", "a_x", "hh"]
    df = pd.DataFrame(0.0, index=idx, columns=cols)
    df["desc"] = "label"                       # non-numeric first column, like the real SAM
    # activity columns -> known gross outputs
    df.loc["c_x", "a_e"] = 10; df.loc["va", "a_e"] = 90      # a_e gross = 100
    df.loc["c_x", "a_w"] = 4;  df.loc["va", "a_w"] = 16      # a_w gross = 20
    df.loc["c_x", "a_x"] = 30; df.loc["va", "a_x"] = 50      # a_x gross = 80
    # commodity rows -> known absorption (over a_* and hh)
    df.loc["c_e", "a_x"] = 5;  df.loc["c_e", "hh"] = 15      # c_e absorption = 20
    df.loc["c_w", "a_x"] = 2;  df.loc["c_w", "hh"] = 8       # c_w absorption = 10
    df.loc["c_x", "hh"] = 50                                  # c_x absorption = 50 (+ activity uses)
    # a 'total' aggregate row that must be ignored (equals the column gross): proves de-dup
    df.loc["total", "a_e"] = 100; df.loc["total", "a_w"] = 20; df.loc["total", "a_x"] = 80
    return df


PROD = {"Utilities": ["a_e", "a_w"], "Other": ["a_x"]}
CONS = {"EnergyWater": ["c_e", "c_w"], "Other": ["c_x"]}


# --- production-side shares -----------------------------------------------------------------

def test_production_share_joined(sam):
    sh = ag.shares(sam, PROD, ["a_e"], axis="production")
    assert not sh.split
    g = sh.groups[0]
    assert g.index == 0 and g.name == "Utilities"
    assert g.share == pytest.approx(100 / 120)          # a_e / (a_e + a_w)


def test_total_row_is_ignored(sam):
    # the injected 'total' row would double gross output; share must be unaffected
    sh = ag.shares(sam, PROD, ["a_w"], axis="production")
    assert sh.groups[0].share == pytest.approx(20 / 120)


def test_weighted_shock_is_share_times_shock(sam):
    plan = ag.weighted_shock(sam, PROD, ["a_e"], 0.30, axis="production")
    t = plan.targets[0]
    assert t.weighted_shock == pytest.approx(0.30 * 100 / 120)
    assert not t.diluted and plan.warnings == []        # 83% dominates -> no warning


def test_dilution_warns(sam):
    plan = ag.weighted_shock(sam, PROD, ["a_w"], 0.30, axis="production")
    t = plan.targets[0]
    assert t.diluted and t.share == pytest.approx(20 / 120)
    assert plan.warnings and "cannot be read as" in plan.warnings[0]


# --- consumption-side shares + tax-base weighting -------------------------------------------

def test_consumption_share_total_absorption(sam):
    sh = ag.shares(sam, CONS, ["c_e"], axis="consumption")
    assert sh.groups[0].share == pytest.approx(20 / 30)  # c_e / (c_e + c_w)


def test_consumption_share_household_base(sam):
    # restrict the tax base to household columns: c_e hh=15, c_w hh=8
    sh = ag.shares(sam, CONS, ["c_e"], axis="consumption", weight_cols=["hh"])
    assert sh.groups[0].share == pytest.approx(15 / 23)


# --- isolated, split, not-found, model_m ----------------------------------------------------

def test_isolated_subgood_is_clean(sam):
    plan = ag.weighted_shock(sam, {"Energy": ["a_e"]}, ["a_e"], 0.20, axis="production")
    assert plan.targets[0].share == pytest.approx(1.0)
    assert not plan.targets[0].diluted and plan.warnings == []
    assert "clean pass-through" in plan.targets[0].note


def test_split_subgood_warns_and_targets_each(sam):
    split_cons = {"A": ["c_e"], "B": ["c_w"], "C": ["c_x"]}
    # a regex that matches c_e and c_w (two groups) -> split
    plan = ag.weighted_shock(sam, split_cons, r"^c_[ew]$", 0.10, axis="consumption")
    assert plan.split and len(plan.targets) == 2
    assert any("split across 2 groups" in w for w in plan.warnings)


def test_not_found_raises(sam):
    with pytest.raises(ValueError, match="matched no codes"):
        ag.shares(sam, PROD, ["zzz"], axis="production")


def test_model_m_out_of_range_raises(sam):
    with pytest.raises(ValueError, match="out of range for M=1"):
        ag.weighted_shock(sam, PROD, ["a_x"], 0.2, axis="production", model_m=1)


def test_model_m_mismatch_warns(sam):
    # 2-group aggregation but the model is told it runs M=3 -> indices may not align
    plan = ag.weighted_shock(sam, PROD, ["a_e"], 0.2, axis="production", model_m=3)
    assert plan.targets[0].index == 0          # in range for M=3
    assert any("runs M=3" in w for w in plan.warnings)


# --- carrier matching is axis-agnostic and convention-robust --------------------------------

@pytest.mark.parametrize("codes,expect", [
    (["aelec", "awatr", "ahotl"], ["aelec"]),    # PHL/IDN/ETH activity
    (["aelcg", "awatd", "amine"], ["aelcg"]),    # ZAF activity (no 'elec' substring!)
    (["celec", "cwatr", "cmine"], ["celec"]),    # commodity
    (["celcg", "celcm", "celcd"], ["celcg", "celcm", "celcd"]),  # ZAF split electricity
])
def test_electricity_carrier_matches_across_conventions(codes, expect):
    assert ag._match_codes({"g": codes}, "electricity") == expect


def test_aggregation_groups_indexing():
    groups = ag.aggregation_groups({"A": ["x"], "B": ["y", "z"]})
    assert groups == [(0, "A", ["x"]), (1, "B", ["y", "z"])]


def test_apply_productivity_haircut():
    # minimal SAM where activity "a" is the whole "Energy" group -> share 1.0 on index 1
    mini = pd.DataFrame({"desc": ["x"], "a": [1.0]}, index=["r"])
    plan = ag.weighted_shock(mini, {"Other": ["o"], "Energy": ["a"]}, ["a"], 0.10, axis="production")
    p = type("P", (), {})()
    p.Z = np.ones((3, 2))
    prov = ag.apply_productivity_haircut(p, plan)
    assert np.allclose(p.Z[:, 1], 0.90)        # index 1 haircut by 10%
    assert np.allclose(p.Z[:, 0], 1.0)         # index 0 untouched
    assert prov["applied"] == [(1, pytest.approx(0.10))]


# --- local integration: the real PHL/IDN/ZAF/ETH calibrations -------------------------------

def _load_real(repo):
    base = os.path.expanduser(f"~/Projects/{repo}")
    sam_csv = glob.glob(f"{base}/*/data/*SAM*.csv")
    const = glob.glob(f"{base}/*/constants.py")
    if not sam_csv or not const:
        return None
    sam = pd.read_csv(sam_csv[0], index_col=1, thousands=",").fillna(0)
    src = _committed_source(base, const[0])   # base on UPSTREAM/committed, not a country repo's local WIP

    def load(name):
        for node in ast.parse(src).body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
                return ast.literal_eval(node.value)
        return None
    return sam, load("PROD_DICT"), load("CONS_DICT")


def _committed_source(repo, path):
    """The UPSTREAM text of ``path`` -- prefer ``origin/main`` (the stable upstream, so the test is robust
    to the local checkout being on a feature branch / open PR), then ``HEAD``, then the working tree. So
    these real-package tests assert the upstream calibration, not whatever branch/WIP a country repo
    happens to be on."""
    import subprocess
    rel = os.path.relpath(path, repo)
    for ref in ("origin/main", "HEAD"):
        try:
            r = subprocess.run(["git", "-C", repo, "show", f"{ref}:{rel}"], capture_output=True, text=True,
                               check=False)
            if r.returncode == 0 and r.stdout:
                return r.stdout
        except Exception:  # noqa: BLE001 -- ref/git unavailable -> try the next fallback
            pass
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.mark.parametrize("repo,exp_index,exp_share", [
    ("OG-PHL", 2, 0.79),    # UPSTREAM/committed: electricity joined with water in "Utilities" (aelec+awatr)
    ("OG-IDN", 2, 0.90),    # electricity in joined "Utilities" (aelec + awatr)
    ("OG-ZAF", 1, 1.00),    # electricity isolated as "Energy" (aelcg)
    ("OG-ETH", 1, 1.00),    # electricity isolated as "Energy" (aelec)
])
def test_real_electricity_industry_share(repo, exp_index, exp_share):
    loaded = _load_real(repo)
    if loaded is None:
        pytest.skip(f"{repo} not present locally")
    sam, prod, _ = loaded
    plan = ag.weighted_shock(sam, prod, "electricity", 0.20, axis="production")
    assert not plan.split
    t = plan.targets[0]
    assert t.index == exp_index                      # discovered, not declared
    assert t.share == pytest.approx(exp_share, abs=0.02)
    # isolated calibrations are clean; joined ones at ~0.8-0.9 are not diluted (>50%) but noted
    assert t.diluted is False


def test_real_phl_energy_consumption_good_is_mostly_not_electricity():
    loaded = _load_real("OG-PHL")
    if loaded is None:
        pytest.skip("OG-PHL not present locally")
    sam, _, cons = loaded
    plan = ag.weighted_shock(sam, cons, "electricity", 0.20, axis="consumption")
    t = plan.targets[0]
    assert t.share < 0.5 and t.diluted               # ~39%: the "Energy & water" good is mostly mining
    assert plan.warnings


def test_real_apply_on_ogcore_specifications():
    """Full pipeline on a REAL OG-Core Specifications at the calibration's natural M: discover the energy
    index from the COMMITTED PROD_DICT (upstream, not a local WIP working tree), weight the +20% shock,
    apply it, and confirm only that column moves by the weighted amount. Skips if OG-Core / ogphl absent."""
    Specifications = pytest.importorskip("ogcore.parameters").Specifications
    loaded = _load_real("OG-PHL")                     # committed PROD_DICT + SAM (upstream-based)
    if loaded is None:
        pytest.skip("OG-PHL not present locally")
    sam, PROD_DICT, _ = loaded
    p = Specifications()
    p.M = len(PROD_DICT)                              # straight from the committed dict (no hand-picked M)
    p.Z = np.ones((p.T + p.S, p.M)) * 1.5             # a real (T+S, M) Z to haircut
    plan = ag.weighted_shock(sam, PROD_DICT, "electricity", 0.20, axis="production", model_m=p.M)
    t = plan.targets[0]
    # UPSTREAM ogphl joins electricity with water in "Utilities" (index 2, share 0.79)
    assert t.index == 2 and t.share == pytest.approx(0.79, abs=0.02)
    z0 = np.asarray(p.Z, float).copy()
    ag.apply_productivity_haircut(p, plan)
    ratio = np.asarray(p.Z, float)[0] / z0[0]
    moved = [i for i in range(p.M) if not np.isclose(ratio[i], 1.0)]
    assert moved == [t.index]                         # only the energy column moved
    assert np.isclose(ratio[t.index], 1 - t.weighted_shock)
