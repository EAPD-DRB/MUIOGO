"""The auto-generated, self-contained, results-only coupled-run deck: CLEWS-source staging (task #6),
the OG-env deck dispatch (non-fatal), and the results-only defaults (no baked caveat / no hardcoded
magnitudes). numpy/pandas-only (no ogcore/solve)."""
import inspect
import os
from types import SimpleNamespace

from oglink import runtime
from oglink.muiogo_run import stage_clews_source
from oglink.registry import ModelEntry
from oglink.viz import build

# --- task #6: stage the CLEWS source next to the run --------------------------------

_EXPORTS = ["RE1_AnnualTechnologyEmissionByMode_2050.csv", "CapitalInvestment.csv",
            "AnnualizedInvestmentCost.csv", "AnnualFixedOperatingCost.csv",
            "AnnualVariableOperatingCost.csv", "RE1_EBb4_EnergyBalanceEachYear4_ICR.csv",
            "Cost of electricity generation_v9.xlsx"]
_DECOYS = ["ProductionByTechnology.csv", "~$Cost of electricity.xlsx", "notes.txt"]


def _case(root, files):
    os.makedirs(root, exist_ok=True)
    for f in files:
        open(os.path.join(root, f), "w").close()
    return root


def test_stage_copies_deck_allowlist_only(tmp_path):
    base = _case(str(tmp_path / "b"), _EXPORTS + _DECOYS)
    reform = _case(str(tmp_path / "r"), _EXPORTS + _DECOYS)
    dest = str(tmp_path / "run" / "clews_source")
    n = stage_clews_source(base, reform, dest)
    staged = sorted(os.listdir(os.path.join(dest, "base")))
    assert n == 2 * len(_EXPORTS)
    assert staged == sorted(_EXPORTS)                 # every allowlisted export, region/year prefixes intact
    for d in _DECOYS:                                 # decoys + Excel lock-files excluded
        assert d not in staged


def test_stage_missing_dirs_are_safe(tmp_path):
    assert stage_clews_source(None, "/no/such/dir", str(tmp_path / "x")) == 0
    assert not os.path.exists(tmp_path / "x")         # nothing created when there's nothing to stage


def test_stage_reform_only(tmp_path):
    reform = _case(str(tmp_path / "r"), ["CapitalInvestment.csv"])
    dest = str(tmp_path / "cs")
    assert stage_clews_source(None, reform, dest) == 1
    assert os.path.isfile(os.path.join(dest, "reform", "CapitalInvestment.csv"))
    assert not os.path.isdir(os.path.join(dest, "base"))


# --- results-only defaults (no baked caveat / no hardcoded magnitudes) --------------

def test_coupled_deck_defaults_to_real_no_caveat():
    # a coupled run is the REAL integrated result -> illustrative defaults False (no "illustrative" stamp)
    assert inspect.signature(build.build_deck_from_coupled_run).parameters["illustrative"].default is False


def test_default_note_carries_no_hardcoded_magnitudes():
    for banned in ("20%", "$50", "50.0", "Philippines", "PHL"):
        assert banned not in build.DEFAULT_NOTE and banned not in build.FIG_CAVEAT


def test_sector_good_names_gate_on_alignment(monkeypatch):
    # names are recorded ONLY when PROD_DICT/CONS_DICT line up with the solved M/I (positional labels);
    # a mismatch -> None so the figure falls back to numbers rather than mislabel (the PHL M8-vs-M7 case)
    import sys
    import types

    from oglink import og_runner as ogr
    fake = types.ModuleType("fakeog")
    fake.PROD_DICT = {"Agriculture": [], "Electricity": [], "Manufacturing": []}   # 3
    fake.CONS_DICT = {"Food": [], "Energy": []}                                     # 2
    monkeypatch.setitem(sys.modules, "fakeog", fake)
    assert ogr._sector_good_names("fakeog", 3, 2) == (["Agriculture", "Electricity", "Manufacturing"],
                                                      ["Food", "Energy"])
    assert ogr._sector_good_names("fakeog", 8, 2)[0] is None      # PROD_DICT(3) != solved M(8) -> no ind names
    assert ogr._sector_good_names("fakeog", 3, 9)[1] is None      # CONS_DICT(2) != solved I(9) -> no good names
    assert ogr._sector_good_names("no_such_pkg_xyz", 3, 2) == (None, None)   # import fail -> safe


def test_sectoral_reallocation_threads_industry_names(tmp_path, monkeypatch):
    # regression: the figure took industry_names but must PASS it to _sector_labels (a missed thread
    # left the sector figure numbered while goods were named)
    from oglink.viz import plots
    seen = {}
    real = plots._sector_labels
    monkeypatch.setattr(plots, "_sector_labels",
                        lambda M, energy0=None, names=None: (seen.update(names=names) or real(M, energy0, names)))
    ss = {"Y_m": [1.0, 2.0, 3.0], "K_m": [1.0, 2.0, 3.0], "L_m": [1.0, 2.0, 3.0]}
    rss = {"Y_m": [1.01, 2.0, 3.0], "K_m": [1.0, 2.0, 3.0], "L_m": [1.0, 2.0, 3.0]}
    plots.sectoral_reallocation(ss, rss, None, str(tmp_path), industry_names=["Ag", "Elec", "Manuf"])
    assert seen["names"] == ["Ag", "Elec", "Manuf"]


def test_names_from_meta(tmp_path):
    import json
    bd = tmp_path / "base"
    bd.mkdir()
    (bd / "baseline_meta.json").write_text(
        json.dumps({"M": 3, "I": 2, "industry_names": ["A", "B", "C"], "good_names": ["x", "y"]}))
    assert build._names_from_meta(str(bd)) == (["A", "B", "C"], ["x", "y"])
    b2 = tmp_path / "b2"
    b2.mkdir()
    (b2 / "baseline_meta.json").write_text(json.dumps({"M": 3}))     # older meta, no names
    assert build._names_from_meta(str(b2)) == (None, None)
    assert build._names_from_meta(str(tmp_path / "nope")) == (None, None)   # no meta file


def test_cli_coupled_path_is_real_by_default(monkeypatch):
    # the CLI must not force illustrative=True into a coupled deck (the function default is False)
    seen = {}
    monkeypatch.setattr(build, "build_deck_from_coupled_run", lambda *a, **k: seen.update(k))
    build.main(["--coupled-run", "/tmp/x", "--country", "phl"])
    assert seen["illustrative"] is False and seen["note"] in (None, "")
    seen.clear()
    build.main(["--coupled-run", "/tmp/x", "--country", "phl", "--illustrative"])
    assert seen["illustrative"] is True


# --- OG-env deck dispatch: correct args, and NON-FATAL on failure -------------------

def _entry(py="/nonexistent/python"):
    return ModelEntry(key="og-x", package="ogx", env_python=py)


def test_build_deck_nonfatal_on_bad_interpreter(tmp_path):
    # a missing interpreter must NOT raise (a deck failure can never fail a completed solve)
    assert runtime.build_deck(_entry(), str(tmp_path), country_selector="og-x") is False


def test_build_deck_dispatches_expected_args(tmp_path, monkeypatch):
    seen = {}

    def fake_run(argv, **kw):
        seen["argv"] = argv
        return SimpleNamespace(returncode=0, stdout="built")

    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    ok = runtime.build_deck(_entry("/py"), str(tmp_path / "run"), country_selector="og-zaf",
                            countries_file="/cfg/countries.json", out_dir=str(tmp_path / "out"))
    assert ok is True
    a = seen["argv"]
    assert a[0] == "/py" and a[1:3] == ["-m", "oglink.viz"]
    assert "--coupled-run" in a and "--country" in a and a[a.index("--country") + 1] == "og-zaf"
    assert a[a.index("--countries") + 1] == "/cfg/countries.json"
    assert a[a.index("--out-dir") + 1] == str(tmp_path / "out")


def test_build_deck_reports_failure_but_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime.subprocess, "run",
                        lambda argv, **kw: SimpleNamespace(returncode=2, stdout="boom\ntraceback"))
    log = str(tmp_path / "deck_build.log")
    assert runtime.build_deck(_entry("/py"), str(tmp_path), country_selector="og-x", log_path=log) is False
    assert os.path.isfile(log)                        # the failure output is persisted for debugging
