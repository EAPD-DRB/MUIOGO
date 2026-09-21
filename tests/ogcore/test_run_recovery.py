"""Stopping a run cleanly, and recovering one the server left behind.

A solve is spawned detached so it can be tree-killed, which also means a server
stop would orphan it unless told otherwise, and a crash leaves the run reading as
running with nobody behind it.
"""
import subprocess
import sys
import threading
import time

from Classes.Base import Config
import Classes.OGCore.OGRunner as OGRunnerMod
from Classes.OGCore.OGRunner import OGRunner, kill_worker_tree
from Classes.OGCore.RunJob import RunJob

from .conftest import wait_idle


# ── stopping the active run ──────────────────────────────────────────────────
def test_stop_active_is_a_noop_when_idle():
    assert RunJob.stop_active() is False


def test_stop_active_kills_the_worker_and_finalises(
    make_case, calibration, fake_runner
):
    case = make_case("c1", runs=[("base", "baseline", None)])
    RunJob.start("ETH", "c1", "base", False)
    assert fake_runner[0].spawned.wait(5)

    assert RunJob.stop_active() is True

    assert fake_runner[0].killed is True
    assert wait_idle(), "the supervision thread finished"
    meta = case.get_run_meta("base")
    assert meta["status"] == "failed" and meta["error"] == "Cancelled by user."


# ── the worker pid is recorded, then cleared ─────────────────────────────────
def test_worker_pid_is_recorded_while_running_and_cleared_after(
    make_case, calibration, fake_runner
):
    case = make_case("c1", runs=[("base", "baseline", None)])
    RunJob.start("ETH", "c1", "base", False)
    assert fake_runner[0].spawned.wait(5)
    # The pid is written just after the spawn returns, so wait for it to land.
    deadline = time.time() + 5
    while time.time() < deadline and case.get_run_meta("base").get("pid") is None:
        time.sleep(0.02)
    assert case.get_run_meta("base")["pid"] is not None

    fake_runner[0].finish(rc=1)
    assert wait_idle()
    assert case.get_run_meta("base")["pid"] is None, "a finished run keeps no pid"


# ── restart recovery ─────────────────────────────────────────────────────────
def test_reconcile_fails_a_run_left_running(make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("later", "reform", "base", {})
    case.update_run_status("base", "running")  # as a crash would leave it
    case.set_run_pid("base", 999999)           # long gone

    RunJob.reconcile_interrupted_runs()

    meta = case.get_run_meta("base")
    assert meta["status"] == "failed"
    assert "restart" in (meta["error"] or "").lower()
    assert case.get_run_meta("later")["status"] == "pending", "untouched"


def test_reconcile_fails_a_run_left_queued(make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "queued")

    RunJob.reconcile_interrupted_runs()

    meta = case.get_run_meta("base")
    assert meta["status"] == "failed"
    assert "queued" in meta["error"].lower()
    assert "restart" in meta["error"].lower()


def test_reconcile_is_idempotent_and_leaves_finished_runs(make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "completed", time_path=False)

    RunJob.reconcile_interrupted_runs()
    RunJob.reconcile_interrupted_runs()

    assert case.get_run_meta("base")["status"] == "completed"


def test_reconcile_survives_one_unreadable_run(make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("second", "reform", "base", {})
    case.update_run_status("second", "running")
    (case.res_path / "base" / "run_meta.json").write_text("{ not json")

    RunJob.reconcile_interrupted_runs()

    assert case.get_run_meta("second")["status"] == "failed", "other runs still repaired"


# ── the orphan kill is scoped to that run ────────────────────────────────────
def test_kill_worker_tree_spares_an_unrelated_process(tmp_path):
    proc = _spawn([sys.executable, "-c", "import time; time.sleep(30)"])
    time.sleep(0.4)
    try:
        assert kill_worker_tree(proc.pid, tmp_path) is False
        time.sleep(0.3)
        assert proc.poll() is None, "an unrelated process must survive"
    finally:
        proc.kill()
        proc.wait(timeout=5)


def test_kill_worker_tree_spares_another_runs_worker(tmp_path):
    # A recycled pid belonging to a different run's worker must not be killed.
    other = tmp_path / "base2"
    proc = _spawn(
        [sys.executable, "-c", "import time; time.sleep(30)", "ogc_worker.py",
         "--run-dir", str(other)]
    )
    time.sleep(0.4)
    try:
        assert kill_worker_tree(proc.pid, tmp_path / "base") is False
        assert proc.poll() is None
    finally:
        proc.kill()
        proc.wait(timeout=5)


def test_kill_worker_tree_kills_this_runs_worker(tmp_path):
    mine = tmp_path / "this_run"
    proc = _spawn(
        [sys.executable, "-c", "import time; time.sleep(30)", "ogc_worker.py",
         "--run-dir", str(mine)]
    )
    time.sleep(0.4)
    try:
        assert kill_worker_tree(proc.pid, mine) is True
        proc.wait(timeout=10)
        assert proc.poll() is not None
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_kill_worker_tree_handles_no_pid(tmp_path):
    assert kill_worker_tree(None, tmp_path) is False
    assert kill_worker_tree(0, tmp_path) is False


# ── run ceilings ─────────────────────────────────────────────────────────────
def _spawn(cmd, **extra):
    """Spawn a child the way OGRunner does.

    start_new_session matters here: the kill paths use os.killpg on POSIX, so a child
    left in pytest's own process group would take the test run down with it.
    """
    kwargs = dict(extra)
    if Config.SYSTEM != "Windows":
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def _attach(runner, cmd):
    runner.proc = _spawn(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0
    )
    runner._last_activity = time.monotonic()
    runner._reader = threading.Thread(target=runner._read_loop, daemon=True)
    runner._reader.start()


def _runner_with(cmd):
    r = OGRunner()
    _attach(r, cmd)
    return r


def test_inactivity_ceiling_is_off_by_default():
    assert OGRunnerMod.RUN_INACTIVITY_TIMEOUT_SECONDS == 0.0


def test_run_finishing_normally_is_not_flagged():
    r = _runner_with([sys.executable, "-c", "print('done')"])
    try:
        assert r.supervise() == 0
        assert r.stalled is False and r.timed_out is False
    finally:
        if r.proc.poll() is None:
            r.proc.kill()


def test_silent_run_hits_the_inactivity_ceiling(monkeypatch):
    monkeypatch.setattr(OGRunnerMod, "RUN_INACTIVITY_TIMEOUT_SECONDS", 2.0)
    monkeypatch.setattr(OGRunnerMod, "RUN_TIMEOUT_SECONDS", 3600)
    r = _runner_with([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        assert r.supervise() == 124
        assert r.stalled is True and r.timed_out is False
    finally:
        if r.proc.poll() is None:
            r.proc.kill()


def test_chatty_run_is_not_called_stalled(monkeypatch):
    monkeypatch.setattr(OGRunnerMod, "RUN_INACTIVITY_TIMEOUT_SECONDS", 5.0)
    monkeypatch.setattr(OGRunnerMod, "RUN_TIMEOUT_SECONDS", 3600)
    code = ("import time,sys\n"
            "for i in range(6):\n"
            "    print(i); sys.stdout.flush(); time.sleep(0.5)\n")
    r = _runner_with([sys.executable, "-c", code])
    try:
        assert r.supervise() == 0 and r.stalled is False
    finally:
        if r.proc.poll() is None:
            r.proc.kill()


def test_run_exceeding_the_wall_clock_is_stopped(monkeypatch):
    monkeypatch.setattr(OGRunnerMod, "RUN_TIMEOUT_SECONDS", 2)
    monkeypatch.setattr(OGRunnerMod, "RUN_INACTIVITY_TIMEOUT_SECONDS", 0.0)
    r = _runner_with([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        assert r.supervise() == 124
        assert r.timed_out is True and r.stalled is False
    finally:
        if r.proc.poll() is None:
            r.proc.kill()


def test_a_stalled_run_says_so(make_case, calibration, fake_runner):
    case = make_case("c1", runs=[("base", "baseline", None)])
    RunJob.start("ETH", "c1", "base", False)
    assert fake_runner[0].spawned.wait(5)
    fake_runner[0].stalled = True

    fake_runner[0].finish(rc=124)

    assert wait_idle()
    assert "no output" in case.get_run_meta("base")["error"].lower()


def test_worker_is_spawned_unbuffered(make_case, calibration, monkeypatch, tmp_path):
    """Without -u the child block-buffers stdout into the pipe, so a long solve
    would report no progress at all until it finished."""
    seen = {}

    class _Popen:
        def __init__(self, cmd, **kwargs):
            seen["cmd"] = cmd
            self.pid = 1
            self.stdout = None

        def poll(self):
            return 0

    monkeypatch.setattr(OGRunnerMod.subprocess, "Popen", _Popen)
    runner = OGRunner()
    runner._read_loop = lambda: None
    runner.spawn("py", tmp_path / "run")

    assert "-u" in seen["cmd"]
    assert seen["cmd"].index("-u") < seen["cmd"].index(str(OGRunnerMod.WORKER_PATH)), \
        "-u must be an interpreter flag, before the script"


def test_worker_output_streams_live(tmp_path, monkeypatch):
    """The point of -u, through the real spawn: a solve that prints and keeps working
    must be visible while it runs, not only once it exits."""
    stand_in = tmp_path / "ogc_worker.py"
    # No flush, exactly like ogcore's own prints.
    stand_in.write_text(
        "import time\n"
        "print('Iteration: 1')\n"
        "time.sleep(6)\n"
    )
    monkeypatch.setattr(OGRunnerMod, "WORKER_PATH", stand_in)

    runner = OGRunner()
    runner.spawn(sys.executable, tmp_path / "run")   # the production path
    try:
        deadline = time.time() + 3
        while time.time() < deadline and runner.iteration is None:
            time.sleep(0.05)
        assert runner.iteration == 1, "progress must arrive while the run is going"
    finally:
        runner.kill_tree()
        if runner.proc.poll() is None:
            runner.proc.kill()
        runner.proc.wait(timeout=5)


# ── shutdown wiring ──────────────────────────────────────────────────────────
def test_shutdown_stops_the_active_run(make_case, calibration, fake_runner):
    import app as app_module

    make_case("c1", runs=[("base", "baseline", None)])
    RunJob.start("ETH", "c1", "base", False)
    assert fake_runner[0].spawned.wait(5)

    app_module._stop_inflight_work()

    assert fake_runner[0].killed is True, "server shutdown must stop the solve too"
    assert wait_idle()


def test_shutdown_is_a_noop_when_nothing_is_running():
    import app as app_module
    app_module._stop_inflight_work()  # must not raise with no run and no install


def test_shutdown_handlers_cover_both_kinds_of_work():
    import app as app_module
    # Installs and runs are both spawned detached, so cleanup has to cover both.
    assert app_module._stop_inflight_work.__doc__
    src = app_module._stop_inflight_work.__code__.co_names
    assert "_stop_inflight_run" in src and "_stop_inflight_installs" in src


# ── env-var parsing must not stop the app from starting ──────────────────────
def test_timeout_env_falls_back_on_anything_unusable(monkeypatch):
    from Classes.OGCore.OGRunner import _timeout_from_env

    monkeypatch.setenv("X_T", "abc")
    assert _timeout_from_env("X_T", 600) == 600, "a typo must not raise at import"
    monkeypatch.setenv("X_T", "-5")
    assert _timeout_from_env("X_T", 600) == 600, "negative is treated as unset"
    monkeypatch.setenv("X_T", "  90 ")
    assert _timeout_from_env("X_T", 600) == 90
    monkeypatch.delenv("X_T")
    assert _timeout_from_env("X_T", 600) == 600
