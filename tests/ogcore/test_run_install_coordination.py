"""Runs and installs must not touch the same calibration at once.

An install or update rewrites the calibration's venv in place, so a run must not
start against one that is being installed, and an install over a calibration that
is already there must not start while a run is using it.
"""
import pytest

from Classes.OGCore import OGTables
from Classes.OGCore import RunJob as RunJobModule
from Classes.OGCore.CalibrationCatalog import CalibrationCatalog
from Classes.OGCore.CalibrationRegistry import CalibrationRegistry
from Classes.OGCore.InstallJob import InstallJob
from Classes.OGCore.RunJob import RunJob


def _both_resolvers(case):
    """The run layer's and the table layer's view of the same calibration."""
    _, _, run_err = RunJob._resolve_country_env(case)
    _, table_err = OGTables.resolve_python(case)
    return run_err, table_err


# ── a run will not start against a calibration being installed ───────────────
@pytest.mark.parametrize("state", ["installing", "checking"])
def test_run_refused_while_an_install_is_in_flight(make_case, calibration, state):
    case = make_case("c1")
    CalibrationRegistry.update_fields("ETH", install_state=state)

    run_err, table_err = _both_resolvers(case)

    assert "being installed or updated" in run_err
    assert run_err == table_err, "both resolvers refuse identically"


def test_failed_install_says_reinstall_not_wait(make_case, calibration):
    # A failed record is terminal and has no usable environment, so telling the user
    # to wait for it would be wrong: they need to reinstall.
    case = make_case("c1")
    CalibrationRegistry.update_fields(
        "ETH", install_state="failed", python_path=None, venv_path=None,
    )

    run_err, table_err = _both_resolvers(case)

    assert "reinstall" in run_err
    assert run_err == table_err


@pytest.mark.parametrize("state", ["installed", "update_available"])
def test_run_allowed_for_a_working_install(make_case, calibration, state):
    case = make_case("c1")
    CalibrationRegistry.update_fields("ETH", install_state=state)

    run_err, table_err = _both_resolvers(case)

    assert run_err is None and table_err is None


def test_run_refused_while_an_update_is_in_flight(make_case, calibration):
    # The record still says installed and its python_path still exists during an
    # update, so the in-flight job is the only thing that reveals it.
    case = make_case("c1")
    with InstallJob._lock:
        InstallJob._active_by_country["ETH"] = "install_x"

    run_err, table_err = _both_resolvers(case)

    assert "being installed or updated" in run_err
    assert run_err == table_err


def test_gate_wording_matches_across_layers():
    # The two layers hold the gate separately by design, so pin them together here.
    assert OGTables._NOT_RUNNABLE_STATES == RunJobModule._NOT_RUNNABLE_STATES
    assert OGTables._BEING_INSTALLED_MESSAGE == RunJobModule._BEING_INSTALLED_MESSAGE


# ── is_country_running ───────────────────────────────────────────────────────
def test_country_not_running_when_idle(make_case, calibration):
    make_case("c1")
    assert RunJob.is_country_running("ETH") is False
    assert RunJob.is_country_running("") is False


def test_country_running_for_the_active_run(make_case, calibration, stub_launch):
    make_case("c1", runs=[("base", "baseline", None)])
    RunJob.start("ETH", "c1", "base", False)
    assert RunJob.is_country_running("ETH") is True
    assert RunJob.is_country_running("ZAF") is False


def test_country_running_for_a_queued_run(make_case, calibration, tmp_path,
                                         stub_launch):
    # The queued run must be a DIFFERENT country from the active one, or this passes
    # on the active branch alone and never exercises the queue.
    CalibrationRegistry.upsert({
        "country_id": "ZAF", "country_name": "South Africa", "source_type": "catalog",
        "python_path": str(calibration), "venv_path": str(tmp_path / ".venv"),
        "package_name": "ogzaf", "install_state": "installed",
    })
    make_case("c1", country_id="ETH", runs=[("base", "baseline", None)])
    make_case("c2", country_id="ZAF", runs=[("base", "baseline", None)])
    RunJob.start("ETH", "c1", "base", False)   # active   -> ETH
    RunJob.start("ZAF", "c2", "base", False)   # queued   -> ZAF

    assert RunJob.is_country_running("ZAF") is True, "the queue must be searched too"
    assert RunJob.is_country_running("ETH") is True


def test_country_running_holds_even_when_the_case_is_unreadable(calibration):
    """The country comes from the run's own key, not from the case on disk.

    An unreadable case must not hide its own live run from this check, or an install
    would rewrite the venv under a running worker.
    """
    with RunJob._lock:
        RunJob._active = {"country_id": "ETH", "casename": "ghost", "run_name": "r",
                          "runner": None, "thread": None, "cancelled": False}

    assert RunJob.is_country_running("ETH") is True
    assert RunJob.is_country_running("ZAF") is False


# ── an update will not start while a run is using the calibration ────────────
def test_update_refused_while_a_run_is_using_it(
    client, make_case, calibration, stub_launch, tmp_path
):
    make_case("c1", runs=[("base", "baseline", None)])
    CalibrationRegistry.update_fields(
        "ETH", local_path=str(tmp_path / "OG-ETH"),
        repo_url="https://github.com/EAPD-DRB/OG-ETH", source_type="catalog",
    )
    RunJob.start("ETH", "c1", "base", False)

    resp = client.post("/ogc/refreshCalibration",
                       json={"country_id": "ETH", "check_only": False})

    assert resp.status_code == 400
    assert "model run is using this calibration" in resp.get_json()["message"]


def test_update_allowed_once_no_run_is_using_it(
    client, make_case, calibration, tmp_path, monkeypatch
):
    make_case("c1", runs=[("base", "baseline", None)])
    CalibrationRegistry.update_fields(
        "ETH", local_path=str(tmp_path / "OG-ETH"),
        repo_url="https://github.com/EAPD-DRB/OG-ETH", source_type="catalog",
    )
    started = {}
    monkeypatch.setattr(
        InstallJob, "start_install",
        classmethod(lambda cls, **kw: started.update(kw) or
                    {"install_id": "install_2026_01_01_001", "install_state": "checking"}),
    )

    resp = client.post("/ogc/refreshCalibration",
                       json={"country_id": "ETH", "check_only": False})

    assert resp.status_code == 200
    assert started["country_id"] == "ETH", "the update actually started"


def test_install_over_an_existing_calibration_refused_while_running(
    client, make_case, calibration, stub_launch, monkeypatch
):
    monkeypatch.setattr(
        CalibrationCatalog, "find_entry",
        classmethod(lambda cls, key: {
            "country_id": "ETH", "country_name": "Ethiopia",
            "repo_url": "https://github.com/EAPD-DRB/OG-ETH", "package_name": "ogeth",
        }),
    )
    make_case("c1", runs=[("base", "baseline", None)])
    RunJob.start("ETH", "c1", "base", False)

    resp = client.post("/ogc/installCalibration",
                       json={"source_type": "catalog", "country_id": "ETH",
                             "catalog_key": "og-eth"})

    assert resp.status_code == 400
    assert "model run is using this calibration" in resp.get_json()["message"]


def test_repo_url_install_refused_while_running(
    client, make_case, calibration, stub_launch
):
    make_case("c1", runs=[("base", "baseline", None)])
    RunJob.start("ETH", "c1", "base", False)

    resp = client.post("/ogc/installCalibration",
                       json={"source_type": "repo_url", "country_id": "ETH",
                             "country_name": "Ethiopia",
                             "repo_url": "https://github.com/EAPD-DRB/OG-ETH"})

    assert resp.status_code == 400
    assert "model run is using this calibration" in resp.get_json()["message"]


def test_local_register_refused_while_running(
    client, make_case, calibration, stub_launch, tmp_path
):
    # Registering re-syncs the venv, so it needs the gate as much as an install does.
    folder = tmp_path / "OG-ETH"
    folder.mkdir()
    make_case("c1", runs=[("base", "baseline", None)])
    RunJob.start("ETH", "c1", "base", False)

    resp = client.post("/ogc/registerLocalCalibration",
                       json={"country_id": "ETH", "country_name": "Ethiopia",
                             "local_path": str(folder)})

    assert resp.status_code == 400
    assert "model run is using this calibration" in resp.get_json()["message"]
