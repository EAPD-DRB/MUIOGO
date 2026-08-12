"""Run endpoints: input validation, run guards, and restart recovery.

Covers the behaviour a caller can reach without a real solve: bad input is refused
cleanly rather than crashing, a reform cannot run ahead of its baseline, and a run
orphaned by a restart is repaired on the next status read.
"""
from Classes.OGCore.OGCoreCase import OGCoreCase
from Classes.OGCore.RunJob import RunJob


# ── input validation ─────────────────────────────────────────────────────────
def test_run_rejects_malformed_json(client):
    resp = client.post("/ogc/run", data="not json",
                       content_type="application/json")
    assert resp.status_code == 400
    assert resp.get_json()["status_code"] == "error"


def test_run_rejects_missing_fields(client):
    resp = client.post("/ogc/run", json={"casename": "c1"})
    assert resp.status_code == 400
    assert "run_name" in resp.get_json()["message"]


def test_run_rejects_non_boolean_time_path(client, make_case):
    make_case("c1", runs=[("base", "baseline", None)])
    resp = client.post(
        "/ogc/run", json={"casename": "c1", "run_name": "base", "time_path": "yes"}
    )
    assert resp.status_code == 400
    assert "boolean" in resp.get_json()["message"].lower()


def test_run_rejects_path_traversal(client):
    resp = client.post(
        "/ogc/run",
        json={"casename": "../escape", "run_name": "base", "time_path": False},
    )
    assert resp.status_code == 400
    assert resp.get_json()["message"] == "Invalid name."


def test_run_unknown_case_and_run_are_404(client, make_case):
    resp = client.post(
        "/ogc/run", json={"casename": "nope", "run_name": "base", "time_path": False}
    )
    assert resp.status_code == 404

    make_case("c1")
    resp = client.post(
        "/ogc/run", json={"casename": "c1", "run_name": "ghost", "time_path": False}
    )
    assert resp.status_code == 404


def test_get_run_status_unknown_run_is_404(client, make_case):
    make_case("c1")
    resp = client.post("/ogc/getRunStatus",
                       json={"casename": "c1", "run_name": "ghost"})
    assert resp.status_code == 404


def test_cancel_rejects_bad_input(client):
    resp = client.post("/ogc/cancelRun", json={"casename": "c1"})
    assert resp.status_code == 400
    resp = client.post("/ogc/cancelRun",
                       json={"casename": "../x", "run_name": "base"})
    assert resp.status_code == 400


# ── run guards ───────────────────────────────────────────────────────────────
def test_reform_needs_a_completed_baseline(make_case, calibration, stub_launch):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("reform1", "reform", "base", {})

    result = RunJob.start("c1", "reform1", False)

    assert result["status_code"] == "error"
    assert "baseline must complete" in result["message"].lower()
    assert stub_launch == [], "nothing is launched when the guard refuses"


def test_transition_path_reform_needs_a_transition_baseline(
    make_case, calibration, stub_launch
):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "completed", time_path=False)  # steady state only
    case.create_run("reform1", "reform", "base", {})

    result = RunJob.start("c1", "reform1", True)

    assert result["status_code"] == "error"
    assert "transition" in result["message"].lower()


def test_reform_must_match_baseline_dimensions(make_case, calibration, stub_launch):
    case = make_case("c1", runs=[("base", "baseline", None)])
    (case.res_path / "base" / "ogcParams.json").write_text('{"S": 80}')
    case.update_run_status("base", "completed", time_path=True)
    case.create_run("reform1", "reform", "base", {"S": 40})

    result = RunJob.start("c1", "reform1", False)

    assert result["status_code"] == "error"
    assert "same model dimensions" in result["message"].lower()


def test_run_refused_when_calibration_is_not_installed(make_case, stub_launch):
    # No registry record: the run cannot resolve an interpreter.
    make_case("c1", runs=[("base", "baseline", None)])
    result = RunJob.start("c1", "base", False)
    assert result["status_code"] == "error"
    assert "not installed" in result["message"].lower()


# ── restart recovery ─────────────────────────────────────────────────────────
def test_orphaned_running_run_is_repaired_on_status_read(client, make_case):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "running")  # as a crash would leave it

    resp = client.post("/ogc/getRunStatus",
                       json={"casename": "c1", "run_name": "base"})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["run_state"] == "failed"
    assert "restart" in case.get_run_meta("base")["error"].lower()


def test_pending_run_is_left_alone_on_status_read(client, make_case):
    # A created-but-never-started run is legitimately pending; do not repair it.
    case = make_case("c1", runs=[("base", "baseline", None)])

    resp = client.post("/ogc/getRunStatus",
                       json={"casename": "c1", "run_name": "base"})

    assert resp.get_json()["run_state"] == "pending"
    assert case.get_run_meta("base")["status"] == "pending"


def test_results_gate_running_envelope(client, make_case, calibration, stub_launch):
    # An active or queued run has results on the way: the caller gets a spinner.
    make_case("c1", runs=[("base", "baseline", None)])
    RunJob.start("c1", "base", False)

    resp = client.post("/ogc/getMacroTable",
                       json={"casename": "c1", "base_run": "base"})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status_code"] == "running" and body["casename"] == "c1"


def test_results_gate_refuses_a_run_that_never_ran(client, make_case, calibration):
    # Merely pending (created, never started) is not a spinner: there is nothing coming.
    make_case("c1", runs=[("base", "baseline", None)])

    resp = client.post("/ogc/getMacroTable",
                       json={"casename": "c1", "base_run": "base"})

    assert resp.get_json()["status_code"] == "error"


def test_results_gate_unknown_run_is_404(client, make_case, calibration):
    make_case("c1")
    resp = client.post("/ogc/getMacroTable",
                       json={"casename": "c1", "base_run": "ghost"})
    assert resp.status_code == 404


def test_queued_run_reports_queued_stage(client, make_case, calibration, stub_launch):
    make_case("c1", runs=[("base", "baseline", None)])
    make_case("c2", runs=[("base", "baseline", None)])
    RunJob.start("c1", "base", False)
    RunJob.start("c2", "base", False)

    resp = client.post("/ogc/getRunStatus",
                       json={"casename": "c2", "run_name": "base"})

    body = resp.get_json()
    assert body["run_state"] == "queued" and body["run_stage"] == "Queued"
    assert body["queue_position"] == 1


def test_run_status_reports_the_failure_reason(client, make_case, calibration):
    # This is the endpoint a client polls, so it has to say why a run failed.
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "failed", error="Cancelled by user.")

    body = client.post("/ogc/getRunStatus",
                       json={"casename": "c1", "run_name": "base"}).get_json()

    assert body["run_state"] == "failed"
    assert body["error"] == "Cancelled by user."


def test_run_status_error_is_null_for_a_healthy_run(client, make_case, calibration):
    make_case("c1", runs=[("base", "baseline", None)])
    body = client.post("/ogc/getRunStatus",
                       json={"casename": "c1", "run_name": "base"}).get_json()
    assert body["run_state"] == "pending" and body["error"] is None


class _RacingCase:
    """A case that finishes its run between the first meta read and the second.

    Recreates the window the repair has to survive, and records every status write so
    a test can assert the repair was not even attempted.
    """

    def __init__(self, case):
        self._case = case
        self.reads = 0
        self.writes = []

    def get_run_meta(self, run_name):
        self.reads += 1
        status = "running" if self.reads == 1 else "completed"
        return {"status": status, "pid": None, "error": None}

    def update_run_status(self, run_name, status, **kwargs):
        self.writes.append(status)

    def __getattr__(self, item):
        return getattr(self._case, item)


def test_status_read_does_not_fail_a_run_that_just_completed(
    client, make_case, calibration, monkeypatch
):
    """The repair decides on a re-read, so a solve that finishes between the first
    read and the liveness check must not be overwritten as failed."""
    case = make_case("c1", runs=[("base", "baseline", None)])
    racing = _RacingCase(case)
    monkeypatch.setattr(
        "Routes.OGCore.OGCoreRunRoute.OGCoreCase",
        lambda name: racing if name == "c1" else OGCoreCase(name),
    )

    body = client.post("/ogc/getRunStatus",
                       json={"casename": "c1", "run_name": "base"}).get_json()

    assert racing.writes == [], "a finished run must not be repaired at all"
    assert body["run_state"] == "completed"
