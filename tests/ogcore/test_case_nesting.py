"""Cases stored under their country.

A case lives at cases/<country_id>/<casename>, so the name alone does not identify
one. These test the storage layer directly, without the route layer, so a failure
points at the on-disk shape rather than at an endpoint.
"""
import json
import os

import pytest

from Classes.Base import Config
from Classes.OGCore.OGCoreCase import OGCoreCase
from Classes.OGCore.CalibrationRegistry import CalibrationRegistry
from Classes.OGCore.RunJob import RunJob


def _make(country_id, casename, description=""):
    case = OGCoreCase(country_id, casename)
    case.create_case({"ogc-casename": casename, "ogc-description": description})
    return case


# ── the layout ──────────────────────────────────────────────────────────────
def test_a_case_is_stored_under_its_country(client):
    case = _make("ETH", "Baseline")

    assert case.case_path == Config.OGC_CASES_DIR / "ETH" / "Baseline"
    assert (Config.OGC_CASES_DIR / "ETH" / "Baseline" / "genData.json").is_file()
    assert (Config.OGC_CASES_DIR / "ETH" / "Baseline" / "res").is_dir()


def test_two_countries_can_each_hold_a_case_of_the_same_name(client):
    _make("USA", "Baseline", "the US one")
    _make("ETH", "Baseline", "the ETH one")

    by_country = {c["country_id"]: c for c in OGCoreCase.list_cases()}

    assert by_country["USA"]["description"] == "the US one"
    assert by_country["ETH"]["description"] == "the ETH one"
    assert by_country["USA"]["casename"] == by_country["ETH"]["casename"] == "Baseline"


def test_the_same_name_in_one_country_is_still_one_case(client):
    _make("ETH", "Baseline")

    again = OGCoreCase("ETH", "Baseline")

    with pytest.raises(FileExistsError):
        again.create_case({"ogc-casename": "Baseline"})


# ── the country comes from the path ─────────────────────────────────────────
def test_genData_records_the_country_it_is_stored_under(client):
    case = OGCoreCase("ETH", "Baseline")
    case.create_case({"ogc-casename": "Baseline", "country_id": "USA"})

    gd = json.loads(case.gen_data_path.read_text())

    assert gd["country_id"] == "ETH", "the directory wins over the body"


def test_an_edit_cannot_move_a_case_to_another_country(client):
    case = _make("ETH", "Baseline")

    case.save_case({"ogc-casename": "Baseline", "country_id": "USA"})

    assert json.loads(case.gen_data_path.read_text())["country_id"] == "ETH"
    assert (Config.OGC_CASES_DIR / "ETH" / "Baseline").is_dir()
    assert not (Config.OGC_CASES_DIR / "USA").exists()


def test_the_listing_reports_the_country_from_the_directory(client):
    """A genData naming another country must not be believed: the case is not there."""
    case = OGCoreCase("ETH", "Baseline")
    case.create_case({"ogc-casename": "Baseline"})
    gd = json.loads(case.gen_data_path.read_text())
    gd["country_id"] = "USA"
    case.gen_data_path.write_text(json.dumps(gd))

    listed = OGCoreCase.list_cases()

    assert [c["country_id"] for c in listed] == ["ETH"]


def test_the_listing_reports_the_name_from_the_directory(client):
    """A genData naming a different case would address a case nobody can reach."""
    case = _make("ETH", "Baseline")
    gd = json.loads(case.gen_data_path.read_text())
    gd["ogc-casename"] = "SomethingElse"
    case.gen_data_path.write_text(json.dumps(gd))

    assert [c["casename"] for c in OGCoreCase.list_cases()] == ["Baseline"]


# ── listing ─────────────────────────────────────────────────────────────────
def test_the_listing_can_be_narrowed_to_one_country(client):
    _make("USA", "Baseline")
    _make("ETH", "Baseline")
    _make("ETH", "Reform")

    listed = OGCoreCase.list_cases(country_id="ETH")

    assert sorted(c["casename"] for c in listed) == ["Baseline", "Reform"]
    assert {c["country_id"] for c in listed} == {"ETH"}


def test_narrowing_to_a_country_with_no_cases_is_empty_not_an_error(client):
    _make("ETH", "Baseline")

    assert OGCoreCase.list_cases(country_id="USA") == []


def test_an_empty_country_directory_contributes_nothing(client):
    _make("ETH", "Baseline")
    (Config.OGC_CASES_DIR / "USA").mkdir(parents=True)

    listed = OGCoreCase.list_cases()

    assert [c["country_id"] for c in listed] == ["ETH"]


def test_one_unreadable_case_does_not_break_the_listing(client):
    _make("ETH", "Good")
    broken = Config.OGC_CASES_DIR / "ETH" / "Broken"
    broken.mkdir(parents=True)
    (broken / "genData.json").write_text("{not json")

    assert [c["casename"] for c in OGCoreCase.list_cases()] == ["Good"]


def test_a_stray_file_beside_the_country_directories_is_ignored(client):
    _make("ETH", "Baseline")
    (Config.OGC_CASES_DIR / "stray.txt").write_text("not a country")

    assert [c["country_id"] for c in OGCoreCase.list_cases()] == ["ETH"]


def test_listing_an_absent_cases_directory_is_empty(client):
    assert OGCoreCase.list_cases() == []


# ── names ───────────────────────────────────────────────────────────────────
def test_an_unsafe_country_id_is_refused(client):
    result = OGCoreCase("../evil", "Baseline").create_case({"ogc-casename": "Baseline"})

    assert result["status_code"] == "error"
    assert not (Config.OGC_CASES_DIR.parent / "evil").exists()


def test_an_unsafe_case_name_is_still_refused(client):
    result = OGCoreCase("ETH", "..").create_case({"ogc-casename": ".."})

    assert result["status_code"] == "error"


# ── migrating cases stored before nesting ───────────────────────────────────
def _flat_case(casename, country_id=None, description=""):
    """A case in the old layout: straight under the cases directory."""
    case_dir = Config.OGC_CASES_DIR / casename
    (case_dir / "res" / "base").mkdir(parents=True)
    gd = {"ogc-casename": casename, "ogc-description": description,
          "ogc-runs": [], "ogc-version": "1.0"}
    if country_id is not None:
        gd["country_id"] = country_id
    (case_dir / "genData.json").write_text(json.dumps(gd))
    (case_dir / "res" / "base" / "run_meta.json").write_text(
        json.dumps({"run_name": "base", "status": "completed"})
    )
    return case_dir


def test_a_flat_case_moves_under_its_country(client):
    _flat_case("Baseline", "ETH", "carried over")

    assert OGCoreCase.migrate_flat_cases() == 1

    assert not (Config.OGC_CASES_DIR / "Baseline").exists()
    assert (Config.OGC_CASES_DIR / "ETH" / "Baseline" / "genData.json").is_file()
    listed = OGCoreCase.list_cases()
    assert [(c["country_id"], c["casename"]) for c in listed] == [("ETH", "Baseline")]
    assert listed[0]["description"] == "carried over"


def test_migration_carries_runs_and_results_with_the_case(client):
    _flat_case("Baseline", "ETH")

    OGCoreCase.migrate_flat_cases()

    moved = Config.OGC_CASES_DIR / "ETH" / "Baseline" / "res" / "base"
    assert (moved / "run_meta.json").is_file()
    assert OGCoreCase.list_cases()[0]["has_results"] is True


def test_migration_leaves_a_case_with_no_country_alone(client):
    """Guessing a country would hide the case from whichever one really owns it."""
    _flat_case("Orphan", None)

    assert OGCoreCase.migrate_flat_cases() == 0
    assert (Config.OGC_CASES_DIR / "Orphan" / "genData.json").is_file()


def test_migration_moves_several_countries_at_once(client):
    _flat_case("Baseline", "ETH")
    _flat_case("Reform", "USA")

    assert OGCoreCase.migrate_flat_cases() == 2

    assert {(c["country_id"], c["casename"]) for c in OGCoreCase.list_cases()} == {
        ("ETH", "Baseline"), ("USA", "Reform"),
    }


def test_migration_is_idempotent(client):
    _flat_case("Baseline", "ETH")
    OGCoreCase.migrate_flat_cases()

    assert OGCoreCase.migrate_flat_cases() == 0, "a nested case is not migrated again"
    assert len(OGCoreCase.list_cases()) == 1


def test_migration_does_nothing_when_there_is_nothing_to_move(client):
    _make("ETH", "Baseline")

    assert OGCoreCase.migrate_flat_cases() == 0
    assert len(OGCoreCase.list_cases()) == 1


def test_migration_on_an_absent_cases_directory_is_a_no_op(client):
    assert OGCoreCase.migrate_flat_cases() == 0


def test_a_flat_case_named_like_its_own_country_still_moves(client):
    """Source and destination overlap here, which a direct rename cannot do."""
    _flat_case("ETH", "ETH")

    assert OGCoreCase.migrate_flat_cases() == 1

    assert (Config.OGC_CASES_DIR / "ETH" / "ETH" / "genData.json").is_file()
    assert [(c["country_id"], c["casename"]) for c in OGCoreCase.list_cases()] == [
        ("ETH", "ETH")
    ]


def test_migration_does_not_overwrite_a_case_already_nested(client):
    _make("ETH", "Baseline", "the nested one")
    _flat_case("Baseline", "ETH", "the flat one")

    assert OGCoreCase.migrate_flat_cases() == 0

    assert OGCoreCase.list_cases()[0]["description"] == "the nested one"
    assert (Config.OGC_CASES_DIR / "Baseline").exists(), "the flat one is left in place"


def test_migration_leaves_no_staging_directory_behind(client):
    _flat_case("Baseline", "ETH")

    OGCoreCase.migrate_flat_cases()

    staging = Config.OGC_CASES_DIR.parent / "migrate_tmp"
    assert not staging.exists() or list(staging.iterdir()) == []


def test_failed_migration_publish_rolls_the_case_back(client, monkeypatch):
    source = _flat_case("Baseline", "ETH")
    real_replace = os.replace
    calls = 0

    def fail_second_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("publish failed")
        return real_replace(src, dst)

    monkeypatch.setattr("Classes.OGCore.OGCoreCase.os.replace", fail_second_replace)

    assert OGCoreCase.migrate_flat_cases() == 0
    assert source.is_dir()
    assert not (Config.OGC_CASES_DIR / "ETH" / "Baseline").exists()


def test_run_environment_uses_the_directory_country(
    client, calibration, monkeypatch
):
    case = _make("ETH", "Baseline")
    data = case.gen_data
    data["country_id"] = "USA"
    case._write_gen_data(data)
    requested = []

    def lookup(country_id):
        requested.append(country_id)
        return {
            "package_name": "ogcore",
            "commit_sha": None,
            "python_path": str(calibration),
            "install_state": "installed",
        }

    monkeypatch.setattr(CalibrationRegistry, "get", staticmethod(lookup))

    country, python_path, error = RunJob._resolve_country_env(case)

    assert error is None
    assert country["package_name"] == "ogcore"
    assert python_path == str(calibration)
    assert requested == ["ETH"]


# ── runs live under the nested case ─────────────────────────────────────────
def test_runs_are_created_under_the_nested_case(client):
    case = _make("ETH", "Baseline")

    case.create_run("base", "baseline", None, {})

    assert (Config.OGC_CASES_DIR / "ETH" / "Baseline" / "res" / "base").is_dir()
    assert case.get_runs()[0]["RunName"] == "base"


def test_same_named_runs_in_two_countries_stay_apart(client):
    usa = _make("USA", "Baseline")
    eth = _make("ETH", "Baseline")
    usa.create_run("base", "baseline", None, {"frisch": 0.1})
    eth.create_run("base", "baseline", None, {"frisch": 0.9})

    assert usa.get_params("base") == {"frisch": 0.1}
    assert eth.get_params("base") == {"frisch": 0.9}


def test_deleting_a_case_leaves_the_other_country_alone(client):
    _make("USA", "Baseline")
    eth = _make("ETH", "Baseline")

    eth.delete_case()

    assert not (Config.OGC_CASES_DIR / "ETH" / "Baseline").exists()
    assert (Config.OGC_CASES_DIR / "USA" / "Baseline").is_dir()
    assert [c["country_id"] for c in OGCoreCase.list_cases()] == ["USA"]


def test_has_results_is_reported_per_case_not_per_country(client):
    usa = _make("USA", "Baseline")
    eth = _make("ETH", "Baseline")
    usa.create_run("base", "baseline", None, {})
    eth.create_run("base", "baseline", None, {})
    usa.update_run_status("base", "completed")

    by_country = {c["country_id"]: c for c in OGCoreCase.list_cases()}

    assert by_country["USA"]["has_results"] is True
    assert by_country["ETH"]["has_results"] is False
