"""Backend-owned queue reconstruction, dependency safety, and freshness."""

import json
import time

from Classes.OGCore.CalibrationRegistry import CalibrationRegistry
from Classes.OGCore.RunJob import RunJob

from .conftest import wait_idle


def _complete_worker(case, run_name, runner):
    (case.res_path / run_name / "run_status.json").write_text(
        json.dumps({"stage": "complete", "ok": True})
    )
    runner.finish(rc=0)


def test_persisted_queue_and_snapshot_are_reconstructable(
    client, make_case, calibration, stub_launch
):
    make_case("active", runs=[("base", "baseline", None)])
    queued_case = make_case("queued", runs=[("base", "baseline", None)])
    make_case("later", runs=[("base", "baseline", None)])

    RunJob.start("ETH", "active", "base", False)
    RunJob.start("ETH", "queued", "base", False)
    RunJob.start("ETH", "later", "base", True)

    assert queued_case.get_run_meta("base")["status"] == "queued"
    runs = client.post(
        "/ogc/getRuns", json={"country_id": "ETH", "casename": "queued"}
    ).get_json()
    assert runs["baseline"]["status"] == "queued"
    assert runs["baseline"]["queue_position"] == 1

    status = client.post(
        "/ogc/getRunStatus",
        json={"country_id": "ETH", "casename": "later", "run_name": "base"},
    ).get_json()
    assert status["run_state"] == "queued"
    assert status["queue_position"] == 2
    assert status["queue_length"] == 2

    queue = client.post(
        "/ogc/getRunQueue", json={"country_id": "ETH", "casename": "later"}
    ).get_json()
    assert queue["status_code"] == "success"
    assert queue["active"] is None
    assert queue["queued"] == [{
        "country_id": "ETH",
        "casename": "later",
        "run_name": "base",
        "state": "queued",
        "queue_position": 2,
        "time_path": True,
    }]


def test_status_read_fails_an_orphaned_queued_run(client, make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "queued")

    status = client.post(
        "/ogc/getRunStatus",
        json={"country_id": "ETH", "casename": "c1", "run_name": "base"},
    ).get_json()

    assert status["run_state"] == "failed"
    assert "queued" in status["error"].lower()
    assert "restart" in status["error"].lower()


def test_reform_can_queue_behind_its_active_baseline(
    make_case, calibration, fake_runner
):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("reform", "reform", "base", {})

    assert RunJob.start("ETH", "c1", "base", False)["status_code"] == "success"
    assert fake_runner[0].spawned.wait(5)
    queued = RunJob.start("ETH", "c1", "reform", False)

    assert queued["status_code"] == "success"
    assert case.get_run_meta("reform")["status"] == "queued"

    _complete_worker(case, "base", fake_runner[0])
    deadline = time.time() + 5
    while time.time() < deadline and len(fake_runner) < 2:
        time.sleep(0.01)
    assert len(fake_runner) == 2
    assert fake_runner[1].spawned.wait(5)
    assert case.get_run_meta("reform")["status"] == "running"


def test_reform_can_queue_behind_its_already_queued_baseline(
    make_case, calibration, stub_launch
):
    make_case("blocker", runs=[("base", "baseline", None)])
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("reform", "reform", "base", {})

    RunJob.start("ETH", "blocker", "base", False)
    RunJob.start("ETH", "c1", "base", False)
    result = RunJob.start("ETH", "c1", "reform", False)

    assert result["status_code"] == "success"
    assert [item[2] for item in RunJob._queue] == ["base", "reform"]


def test_transition_reform_rejects_preceding_steady_state_baseline(
    make_case, calibration, fake_runner
):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("reform", "reform", "base", {})
    RunJob.start("ETH", "c1", "base", False)
    assert fake_runner[0].spawned.wait(5)

    result = RunJob.start("ETH", "c1", "reform", True)

    assert result["status_code"] == "error"
    assert "transition" in result["message"].lower()


def test_queued_reform_is_revalidated_immediately_before_launch(
    make_case, calibration, fake_runner
):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("reform", "reform", "base", {})
    RunJob.start("ETH", "c1", "base", False)
    assert fake_runner[0].spawned.wait(5)
    RunJob.start("ETH", "c1", "reform", False)

    # Simulate an out-of-band write after admission. The supported API blocks this,
    # but launch-time validation must still defend restored/legacy/external files.
    (case.res_path / "reform" / "ogcParams.json").write_text('{"S": 40}')
    (case.res_path / "base" / "ogcParams.json").write_text('{"S": 80}')
    _complete_worker(case, "base", fake_runner[0])

    assert wait_idle()
    meta = case.get_run_meta("reform")
    assert meta["status"] == "failed"
    assert "same model dimensions" in meta["error"].lower()
    assert len(fake_runner) == 1, "an invalid queued reform must never spawn"


def test_baseline_write_and_rerun_are_blocked_by_queued_dependent_reform(
    client, make_case, calibration, stub_launch
):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "completed", time_path=False)
    case.create_run("reform", "reform", "base", {})
    make_case("blocker", runs=[("base", "baseline", None)])
    RunJob.start("ETH", "blocker", "base", False)
    assert RunJob.start("ETH", "c1", "reform", False)["status_code"] == "success"

    saved = client.post(
        "/ogc/saveParams",
        json={
            "country_id": "ETH", "casename": "c1",
            "run_name": "base", "params": {"S": 40},
        },
    )
    rerun = RunJob.start("ETH", "c1", "base", False)

    assert saved.status_code == 400
    assert "dependent reform" in saved.get_json()["message"].lower()
    assert case.get_params("base") == {}
    assert rerun["status_code"] == "error"
    assert "dependent reform" in rerun["message"].lower()


def test_parameter_change_invalidates_run_and_dependent_reforms(
    client, make_case, calibration
):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "completed", time_path=False)
    case.create_run("reform", "reform", "base", {})
    case.update_run_status("reform", "completed", time_path=False)
    assert case.is_run_reusable("base") is True
    assert case.is_run_reusable("reform") is True

    response = client.post(
        "/ogc/saveParams",
        json={
            "country_id": "ETH", "casename": "c1",
            "run_name": "base", "params": {"S": 40},
        },
    )

    assert response.status_code == 200
    assert case.get_run_meta("base")["status"] == "pending"
    assert case.get_run_meta("reform")["status"] == "pending"
    assert case.is_run_reusable("base") is False
    assert case.is_run_reusable("reform") is False


def test_rerunning_baseline_invalidates_completed_reform(
    make_case, calibration, stub_launch
):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "completed", time_path=False)
    case.create_run("reform", "reform", "base", {})
    case.update_run_status("reform", "completed", time_path=False)

    RunJob.start("ETH", "c1", "base", False)

    reform = case.get_run_meta("reform")
    assert reform["status"] == "pending"
    assert "baseline" in reform["stale_reason"].lower()


def test_calibration_commit_change_makes_completed_result_non_reusable(
    client, make_case, calibration
):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "completed", time_path=False)
    assert case.is_run_reusable("base") is True

    CalibrationRegistry.update_fields("ETH", commit_sha="new-calibration-commit")

    status = client.post(
        "/ogc/getRunStatus",
        json={"country_id": "ETH", "casename": "c1", "run_name": "base"},
    ).get_json()
    runs = client.post(
        "/ogc/getRuns", json={"country_id": "ETH", "casename": "c1"}
    ).get_json()
    assert status["run_state"] == "completed"
    assert status["reusable"] is False
    assert runs["baseline"]["reusable"] is False


def test_legacy_completed_meta_without_fingerprint_is_not_reusable(
    make_case, calibration
):
    case = make_case("c1", runs=[("base", "baseline", None)])
    path = case.res_path / "base" / "run_meta.json"
    meta = case.get_run_meta("base")
    meta["status"] = "completed"
    meta.pop("input_fingerprint", None)
    path.write_text(json.dumps(meta))

    assert case.is_run_reusable("base") is False
