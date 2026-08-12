"""One-solve-at-a-time queueing, and cancelling a run in either state.

The queued-cancel case is the one worth pinning down: dropping the run from the
queue is not enough, because nothing later revisits a "pending" run, so it has to
be written to a terminal state at cancel time or it reads as pending forever.
"""
import json
import time

from Classes.OGCore.RunJob import RunJob

from .conftest import wait_idle


def test_second_run_queues_behind_the_first(make_case, calibration, stub_launch):
    make_case("c1", runs=[("base", "baseline", None)])
    make_case("c2", runs=[("base", "baseline", None)])

    first = RunJob.start("c1", "base", False)
    second = RunJob.start("c2", "base", False)

    assert first["status_code"] == "success" and "started" in first["message"].lower()
    assert second["status_code"] == "success" and "queued" in second["message"].lower()
    assert stub_launch == [("c1", "base")], "only the first run occupies the slot"
    assert RunJob.is_busy("c2", "base") is True


def test_cancel_queued_run_reaches_terminal_state(make_case, calibration, stub_launch):
    case1 = make_case("c1", runs=[("base", "baseline", None)])
    case2 = make_case("c2", runs=[("base", "baseline", None)])
    RunJob.start("c1", "base", False)   # occupies the slot
    RunJob.start("c2", "base", False)   # queued
    assert case2.get_run_meta("base")["status"] == "queued"

    result = RunJob.cancel("c2", "base")

    assert result["status_code"] == "cancelled"
    meta = case2.get_run_meta("base")
    assert meta["status"] == "failed", "a cancelled queued run must not stay pending"
    assert meta["error"] == "Cancelled by user."
    assert meta["completed_at"], "terminal state is stamped"
    assert RunJob.is_busy("c2", "base") is False
    # The run that still holds the slot is untouched.
    assert case1.get_run_meta("base")["status"] == "running"


def test_cancelled_queued_run_does_not_start_when_slot_frees(
    make_case, calibration, stub_launch
):
    make_case("c1", runs=[("base", "baseline", None)])
    case2 = make_case("c2", runs=[("base", "baseline", None)])
    RunJob.start("c1", "base", False)
    RunJob.start("c2", "base", False)
    RunJob.cancel("c2", "base")

    # The active run finishes and the queue is drained.
    with RunJob._lock:
        RunJob._active = None
        RunJob._start_next_locked()

    assert stub_launch == [("c1", "base")], "the cancelled run must not be launched"
    assert case2.get_run_meta("base")["status"] == "failed"


def test_queue_advances_when_the_slot_frees(make_case, calibration, stub_launch):
    make_case("c1", runs=[("base", "baseline", None)])
    case2 = make_case("c2", runs=[("base", "baseline", None)])
    RunJob.start("c1", "base", False)
    RunJob.start("c2", "base", False)

    with RunJob._lock:
        RunJob._active = None
        RunJob._start_next_locked()

    assert stub_launch == [("c1", "base"), ("c2", "base")], "queued run auto-starts"
    assert case2.get_run_meta("base")["status"] == "running"


def test_cancel_active_run_reaches_terminal_state(make_case, calibration, fake_runner):
    """The real thread path: cancel kills the worker and finalizes the run."""
    case = make_case("c1", runs=[("base", "baseline", None)])
    RunJob.start("c1", "base", False)
    assert fake_runner[0].spawned.wait(5), "the worker was spawned"
    assert case.get_run_meta("base")["status"] == "running"

    result = RunJob.cancel("c1", "base")

    assert result["status_code"] == "cancelled"
    assert fake_runner[0].killed is True, "the worker tree is killed"
    assert wait_idle(), "the supervision thread finished and freed the slot"
    meta = case.get_run_meta("base")
    assert meta["status"] == "failed"
    assert meta["error"] == "Cancelled by user."


def test_finished_run_completes_and_frees_the_slot(make_case, calibration, fake_runner):
    case = make_case("c1", runs=[("base", "baseline", None)])
    run_dir = case.res_path / "base"
    RunJob.start("c1", "base", False)
    assert fake_runner[0].spawned.wait(5)
    # The worker owns run_status.json; a completed solve writes its terminal record.
    (run_dir / "run_status.json").write_text(
        json.dumps({"stage": "complete", "ok": True})
    )

    fake_runner[0].finish(rc=0)

    assert wait_idle()
    assert case.get_run_meta("base")["status"] == "completed"


def test_queue_advances_for_real_when_the_active_run_finishes(
    make_case, calibration, fake_runner
):
    """End-to-end: the supervision thread itself starts the next queued run."""
    make_case("c1", runs=[("base", "baseline", None)])
    case2 = make_case("c2", runs=[("base", "baseline", None)])
    RunJob.start("c1", "base", False)
    assert fake_runner[0].spawned.wait(5)
    RunJob.start("c2", "base", False)
    assert case2.get_run_meta("base")["status"] == "queued"

    fake_runner[0].finish(rc=1)  # first run ends; the queue must drain on its own

    end = time.time() + 10
    while time.time() < end and len(fake_runner) < 2:
        time.sleep(0.01)
    assert len(fake_runner) == 2, "the queued run was launched by the run layer"
    assert fake_runner[1].spawned.wait(5)
    assert case2.get_run_meta("base")["status"] == "running"


def test_cancel_queued_run_end_to_end_over_http(
    client, make_case, calibration, fake_runner
):
    """Queue a run, cancel it, read its status back through the API."""
    make_case("c1", runs=[("base", "baseline", None)])
    make_case("c2", runs=[("base", "baseline", None)])
    client.post("/ogc/run",
                json={"casename": "c1", "run_name": "base", "time_path": False})
    assert fake_runner[0].spawned.wait(5)
    queued = client.post(
        "/ogc/run", json={"casename": "c2", "run_name": "base", "time_path": False}
    )
    assert "queued" in queued.get_json()["message"].lower()

    cancelled = client.post("/ogc/cancelRun",
                            json={"casename": "c2", "run_name": "base"})

    assert cancelled.status_code == 200
    assert cancelled.get_json()["status_code"] == "cancelled"
    status = client.post("/ogc/getRunStatus",
                         json={"casename": "c2", "run_name": "base"})
    body = status.get_json()
    assert body["run_state"] == "failed", "not left pending forever"
    assert body["run_stage"] is None


def test_cancel_unknown_run_is_an_error(make_case, calibration):
    make_case("c1", runs=[("base", "baseline", None)])
    result = RunJob.cancel("c1", "base")
    assert result["status_code"] == "error"
    assert "not running or queued" in result["message"].lower()


def test_same_run_cannot_be_queued_twice(make_case, calibration, stub_launch):
    make_case("c1", runs=[("base", "baseline", None)])
    make_case("c2", runs=[("base", "baseline", None)])
    RunJob.start("c1", "base", False)
    RunJob.start("c2", "base", False)

    again = RunJob.start("c2", "base", False)

    assert again["status_code"] == "error"
    assert "already running or queued" in again["message"].lower()
