"""Case and run storage: run ids, the baseline reference, and meta writes.

A run's meta records its baseline by name as well as by path, so a case restored
somewhere else still resolves it; ids are never reused after a delete; and the meta
is written atomically because the status endpoints poll it while a run writes.
"""
import json

from Classes.OGCore.OGCoreCase import OGCoreCase
from Classes.OGCore.RunJob import RunJob


# ── run ids ──────────────────────────────────────────────────────────────────
def test_run_ids_are_not_reused_after_a_delete(make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("r1", "reform", "base", {})
    case.create_run("r2", "reform", "base", {})
    case.delete_run("r1")
    case.create_run("r3", "reform", "base", {})

    ids = {r["RunName"]: r["RunId"] for r in case.get_runs()}
    assert ids["r2"] != ids["r3"], "a deleted run's id must not come back"
    assert len(set(ids.values())) == len(ids), "ids are unique"


# ── portable baseline reference ──────────────────────────────────────────────
def test_reform_records_its_baseline_by_name(make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("reform1", "reform", "base", {})
    assert case.get_run_meta("reform1")["baseline_run_name"] == "base"


def test_baseline_dir_resolves_against_this_case(make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("reform1", "reform", "base", {})
    assert case.baseline_dir("reform1") == case.res_path / "base"


def test_baseline_dir_survives_a_stale_absolute_path(make_case, calibration):
    # What a backup restored from another machine looks like: the stored path points
    # somewhere that does not exist here.
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("reform1", "reform", "base", {})
    meta_path = case.res_path / "reform1" / "run_meta.json"
    meta = json.loads(meta_path.read_text())
    meta["baseline_output_path"] = "/somewhere/else/res/base"
    meta_path.write_text(json.dumps(meta))

    assert case.baseline_dir("reform1") == case.res_path / "base"


def test_baseline_dir_falls_back_to_the_stored_path_leaf(make_case, calibration):
    # A run created before the name was recorded still resolves, via the path leaf.
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("reform1", "reform", "base", {})
    meta_path = case.res_path / "reform1" / "run_meta.json"
    meta = json.loads(meta_path.read_text())
    del meta["baseline_run_name"]
    meta["baseline_output_path"] = "/old/machine/res/base"
    meta_path.write_text(json.dumps(meta))

    assert case.baseline_dir("reform1") == case.res_path / "base"


def test_reform_runs_after_a_restore_with_a_stale_path(
    make_case, calibration, stub_launch
):
    """The guard must read the baseline through the resolved path, not the stale one."""
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "completed", time_path=True)
    case.create_run("reform1", "reform", "base", {})
    meta_path = case.res_path / "reform1" / "run_meta.json"
    meta = json.loads(meta_path.read_text())
    meta["baseline_output_path"] = "/gone/res/base"
    meta_path.write_text(json.dumps(meta))

    result = RunJob.start("c1", "reform1", False)

    assert result["status_code"] == "success", result
    # Launching also repairs the stored path for the worker, which reads this file.
    assert case.get_run_meta("reform1")["baseline_output_path"] == str(
        case.res_path / "base"
    )


# ── reform dimension guard ───────────────────────────────────────────────────
def test_reform_must_match_consumption_goods(make_case, calibration, stub_launch):
    # I (consumption goods) changes comparability just like S/T/J/M.
    case = make_case("c1", runs=[("base", "baseline", None)])
    (case.res_path / "base" / "ogcParams.json").write_text('{"I": 1}')
    case.update_run_status("base", "completed", time_path=True)
    case.create_run("reform1", "reform", "base", {"I": 2})

    result = RunJob.start("c1", "reform1", False)

    assert result["status_code"] == "error"
    assert "same model dimensions" in result["message"].lower()


# ── meta writes ──────────────────────────────────────────────────────────────
def test_run_meta_is_written_atomically(make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "running")
    run_dir = case.res_path / "base"
    assert (run_dir / "run_meta.json").is_file()
    assert not (run_dir / "run_meta.json.tmp").exists(), "temp file is replaced, not left"


def test_unreadable_meta_does_not_break_the_run_listing(make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("reform1", "reform", "base", {})
    (case.res_path / "base" / "run_meta.json").write_text("{ not json")

    runs = {r["RunName"]: r for r in case.get_runs()}

    assert set(runs) == {"base", "reform1"}, "both runs still listed"
    assert runs["base"]["status"] == "pending"
