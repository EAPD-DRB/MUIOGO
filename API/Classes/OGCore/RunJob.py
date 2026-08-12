"""Serialize OG model runs: one solve at a time, ever.

A single active run plus a FIFO queue, guarded by one process-wide lock. Solves are
CPU-and-memory heavy (each spins up its own Dask cluster), so two at once would
thrash the machine; this layer admits exactly one and queues the rest.

Completion is decided from the worker's exit code plus the terminal run_status.json
it wrote (stage "complete", ok True), never from stdout. Single-writer discipline
holds throughout: MUIOGO writes run_meta.json and run_log.txt; the worker owns
run_status.json and the results files, and this layer only reads them.
"""

from __future__ import annotations

import collections
import json
import threading
from pathlib import Path

from Classes.Base import Config
from Classes.OGCore.CalibrationRegistry import CalibrationRegistry
from Classes.OGCore.InstallJob import InstallJob
from Classes.OGCore.OGCoreCase import OGCoreCase
from Classes.OGCore.OGRunner import OGRunner, kill_worker_tree

# States that mean an install is in flight right now. A failed record is not here
# on purpose: it is terminal, and it has no venv_path, so the interpreter check
# below reports it as missing and tells the user to reinstall rather than to wait.
_NOT_RUNNABLE_STATES = {"installing", "checking"}

_BEING_INSTALLED_MESSAGE = (
    "This calibration is being installed or updated. Try again once it finishes."
)

# The model dimensions a reform must share with its baseline. Changing any of them
# leaves the reform describing a different model, so its results are no longer
# comparable: periods, horizon, ability types, industries and consumption goods.
_DIMS = ("S", "T", "J", "M", "I")


def _read_json(path: Path):
    """Read a JSON object from path, tolerating missing/corrupt -> None."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


class RunJob:
    _lock = threading.RLock()
    _active: dict | None = None       # {casename, run_name, runner, thread, cancelled}
    _queue: collections.deque = collections.deque()  # (casename, run_name, time_path)

    # ── run-dir helper ─────────────────────────────────────────────────────
    @staticmethod
    def _run_dir(casename: str, run_name: str) -> Path:
        return OGCoreCase(casename).res_path / run_name

    # ── country / interpreter resolution ───────────────────────────────────
    @staticmethod
    def _resolve_country_env(case: OGCoreCase):
        """Return (country_block, python_path, error).

        error is None on success; otherwise country/python_path are None and error
        is the user-facing message the caller surfaces.
        """
        gd = case.gen_data
        country_id = gd.get("country_id")
        rec = CalibrationRegistry.get(country_id)
        if rec is None:
            return None, None, "That country calibration is not installed."
        # An install or update rewrites the very venv this run would use, so refuse
        # while one is in flight. An update keeps the old python_path on the record,
        # so checking that the path exists is not enough on its own.
        if (InstallJob.is_country_active(country_id)
                or rec.get("install_state") in _NOT_RUNNABLE_STATES):
            return None, None, _BEING_INSTALLED_MESSAGE
        country = {
            "package_name": rec.get("package_name"),
            "is_base": rec.get("package_name") in (None, "", "ogcore"),
            "commit_sha": rec.get("commit_sha"),
        }
        python_path = rec.get("python_path")
        if not python_path or not Path(python_path).exists():
            return None, None, "The calibration's environment is missing; reinstall it."
        return country, python_path, None

    # ── status file read (worker-owned) ────────────────────────────────────
    @staticmethod
    def _read_status(run_dir: Path):
        return _read_json(Path(run_dir) / "run_status.json")

    # ── busy check ─────────────────────────────────────────────────────────
    @classmethod
    def is_busy(cls, casename: str, run_name: str) -> bool:
        with cls._lock:
            act = cls._active
            if act and act["casename"] == casename and act["run_name"] == run_name:
                return True
            return any(
                q[0] == casename and q[1] == run_name for q in cls._queue
            )

    @classmethod
    def case_busy(cls, casename: str) -> bool:
        """True if any run of this case is active or queued.

        Deleting a case while its worker holds files open would corrupt the tree,
        so the delete endpoints refuse while this is true.
        """
        with cls._lock:
            act = cls._active
            if act and act["casename"] == casename:
                return True
            return any(q[0] == casename for q in cls._queue)

    @classmethod
    def _dependent_reform_busy_locked(
        cls, casename: str, baseline_run_name: str
    ) -> bool:
        """Whether live FIFO work depends on this baseline's frozen inputs."""
        candidates = []
        if cls._active and cls._active["casename"] == casename:
            candidates.append(cls._active["run_name"])
        candidates.extend(q[1] for q in cls._queue if q[0] == casename)
        case = OGCoreCase(casename)
        for run_name in candidates:
            meta = case.get_run_meta(run_name)
            if (
                meta.get("run_type") == "reform"
                and meta.get("baseline_run_name") == baseline_run_name
            ):
                return True
        return False

    @classmethod
    def save_params(cls, casename: str, run_name: str, params: dict) -> dict:
        """Atomically guard and persist parameters against FIFO admission."""
        with cls._lock:
            case = OGCoreCase(casename)
            error = cls._parameter_write_error_locked(case, run_name)
            if error:
                return {"status_code": "error", "message": error}
            return case.save_params(run_name, params)

    @classmethod
    def commit_parameter_change(cls, casename: str, run_name: str, writer) -> dict:
        """Publish a prepared parameter file under the same lock as admission."""
        with cls._lock:
            case = OGCoreCase(casename)
            error = cls._parameter_write_error_locked(case, run_name)
            if error:
                return {"status_code": "error", "message": error}
            writer()
            case.invalidate_run(
                run_name, "Parameters changed after the latest completed run."
            )
            return {"status_code": "success"}

    @classmethod
    def _parameter_write_error_locked(
        cls, case: OGCoreCase, run_name: str
    ) -> str | None:
        if cls.is_busy(case.casename, run_name):
            return "Parameters cannot be changed while this run is running or queued."
        meta = case.get_run_meta(run_name)
        if (
            meta.get("run_type") == "baseline"
            and cls._dependent_reform_busy_locked(case.casename, run_name)
        ):
            return (
                "Baseline parameters cannot be changed while a dependent reform "
                "is running or queued."
            )
        return None

    @classmethod
    def is_country_running(cls, country_id: str) -> bool:
        """True if the active or any queued run uses this country's calibration.

        Lets the install layer refuse an update over a calibration a run is using,
        which would rewrite the venv under a live worker. Case names are snapshotted
        under the lock and their genData read outside it, so file reads never hold up
        the run lifecycle.

        Lock order: this takes RunJob._lock, and start() already nests
        RunJob._lock -> InstallJob._lock. The install layer must therefore call this
        without holding InstallJob._lock, or the two orders would deadlock.
        """
        if not country_id:
            return False
        with cls._lock:
            names = set()
            if cls._active:
                names.add(cls._active["casename"])
            names.update(q[0] for q in cls._queue)
        for casename in names:
            try:
                gd = OGCoreCase(casename).gen_data
                if isinstance(gd, dict) and gd.get("country_id") == country_id:
                    return True
            except (OSError, ValueError, KeyError, IndexError):
                continue
        return False

    # ── start ──────────────────────────────────────────────────────────────
    @classmethod
    def start(cls, casename: str, run_name: str, time_path: bool) -> dict:
        """Validate, then either launch immediately or queue the run."""
        with cls._lock:
            case = OGCoreCase(casename)
            meta = case.get_run_meta(run_name)
            if not meta:
                return {"status_code": "error", "message": "Run not found."}

            if cls.is_busy(casename, run_name):
                return {
                    "status_code": "error",
                    "message": "This run is already running or queued.",
                }

            if (
                meta.get("run_type") == "baseline"
                and cls._dependent_reform_busy_locked(casename, run_name)
            ):
                return {
                    "status_code": "error",
                    "message": (
                        "The baseline cannot be run again while a dependent reform "
                        "is running or queued."
                    ),
                }

            if meta.get("run_type") == "reform":
                validation = cls._validate_reform_locked(
                    case, run_name, time_path, allow_preceding_baseline=True
                )
                if validation:
                    return validation

            # Country block + interpreter.
            country, python_path, err = cls._resolve_country_env(case)
            if err:
                return {"status_code": "error", "message": err}

            # Atomic claim, or queue behind the active run.
            if cls._active is None:
                case.stamp_execution(run_name, time_path, country, "running")
                cls._launch(casename, run_name, time_path, python_path)
                return {"status_code": "success", "message": "Run started."}

            case.stamp_execution(run_name, time_path, country, "queued")
            cls._queue.append((casename, run_name, time_path))
            return {
                "status_code": "success",
                "message": "Run queued.",
                "queue_position": len(cls._queue),
            }

    @classmethod
    def _preceding_baseline_time_path_locked(
        cls, casename: str, baseline_run_name: str
    ) -> bool | None:
        act = cls._active
        if (
            act
            and act["casename"] == casename
            and act["run_name"] == baseline_run_name
        ):
            return OGCoreCase(casename).get_run_meta(baseline_run_name).get("time_path")
        for queued_case, queued_run, queued_time_path in cls._queue:
            if queued_case == casename and queued_run == baseline_run_name:
                return queued_time_path
        return None

    @classmethod
    def _validate_reform_locked(
        cls,
        case: OGCoreCase,
        run_name: str,
        time_path: bool,
        *,
        allow_preceding_baseline: bool,
    ) -> dict | None:
        """Validate reform dependencies at admission and again at launch."""
        meta = case.get_run_meta(run_name)
        baseline_dir = case.baseline_dir(run_name)
        baseline_meta = (
            _read_json(baseline_dir / "run_meta.json") if baseline_dir else None
        )
        baseline_name = meta.get("baseline_run_name")
        preceding_time_path = None
        if allow_preceding_baseline and baseline_name:
            preceding_time_path = cls._preceding_baseline_time_path_locked(
                case.casename, baseline_name
            )

        baseline_ready = bool(
            baseline_meta
            and baseline_meta.get("status") == "completed"
            and baseline_name
            and case.is_run_reusable(baseline_name)
        )
        baseline_precedes = preceding_time_path is not None

        if time_path and not (
            (baseline_ready and baseline_meta.get("time_path") is True)
            or (baseline_precedes and preceding_time_path is True)
        ):
            return {
                "status_code": "error",
                "message": (
                    "The baseline must be run with the full transition path "
                    "before this reform."
                ),
            }
        if not baseline_ready and not baseline_precedes:
            return {
                "status_code": "error",
                "message": "The baseline must complete before running a reform.",
            }

        reform_params = _read_json(case.run_params_path(run_name)) or {}
        baseline_params = (
            _read_json(baseline_dir / "ogcParams.json") or {}
        ) if baseline_dir else {}
        for dim in _DIMS:
            in_reform = dim in reform_params
            in_baseline = dim in baseline_params
            if in_reform != in_baseline:
                return cls._dim_mismatch()
            if in_reform and reform_params[dim] != baseline_params[dim]:
                return cls._dim_mismatch()
        return None

    @staticmethod
    def _dim_mismatch() -> dict:
        return {
            "status_code": "error",
            "message": (
                "A reform must use the same model dimensions as its baseline "
                f"({', '.join(_DIMS)})."
            ),
        }

    # ── launch (caller holds the lock) ─────────────────────────────────────
    @classmethod
    def _launch(cls, casename: str, run_name: str, time_path: bool, python_path) -> None:
        """Create the runner, record it active, and start the solve thread.

        The runner is created here (not inside the thread) so cancel() and
        get_live() have a live reference from the instant the run is claimed.
        """
        runner = OGRunner()
        thread = threading.Thread(
            target=cls._run_one,
            args=(casename, run_name, time_path, python_path, runner),
            daemon=True,
        )
        cls._active = {
            "casename": casename,
            "run_name": run_name,
            "runner": runner,
            "thread": thread,
            "cancelled": False,
        }
        thread.start()

    # ── worker supervision thread ──────────────────────────────────────────
    @classmethod
    def _run_one(cls, casename, run_name, time_path, python_path, runner) -> None:
        case = OGCoreCase(casename)
        run_dir = cls._run_dir(casename, run_name)
        try:
            try:
                runner.spawn(python_path, run_dir)
                try:
                    case.set_run_pid(run_name, runner.pid)
                except (OSError, ValueError, KeyError, IndexError):
                    pass  # the run still proceeds; only orphan cleanup needs the pid
                rc = runner.supervise()
            except Exception:
                # Failure to even launch the worker is a run failure, not a crash.
                rc = -1

            status = cls._read_status(run_dir)

            with cls._lock:
                cancelled = bool(cls._active and cls._active.get("cancelled"))

            if cancelled:
                case.update_run_status(run_name, "failed", error="Cancelled by user.")
            elif runner.stalled:
                case.update_run_status(
                    run_name,
                    "failed",
                    error="Run produced no output for too long and was stopped.",
                )
            elif rc == 124 or runner.timed_out:
                case.update_run_status(
                    run_name,
                    "failed",
                    error="Run exceeded the maximum run time and was stopped.",
                )
            elif (
                rc == 0
                and status is not None
                and status.get("stage") == "complete"
                and status.get("ok") is True
            ):
                prov = status.get("provenance")
                if isinstance(prov, dict):
                    case.set_run_provenance(run_name, prov)
                case.update_run_status(run_name, "completed", time_path=time_path)
            else:
                error = None
                if status is not None and status.get("error"):
                    error = status.get("error")
                if not error:
                    error = f"Worker exited with code {rc}."
                case.update_run_status(run_name, "failed", error=error)

            try:
                runner.write_log(run_dir)
            except OSError:
                pass
        finally:
            with cls._lock:
                cls._active = None
                cls._start_next_locked()

    @classmethod
    def _start_next_locked(cls) -> None:
        """Pop and launch the next queued run. Caller holds the lock.

        Drains past any run whose calibration vanished while it waited, marking each
        such run failed, so one broken entry cannot wedge the whole queue.
        """
        while cls._queue:
            casename, run_name, time_path = cls._queue.popleft()
            case = OGCoreCase(casename)
            try:
                meta = case.get_run_meta(run_name)
                if meta.get("run_type") == "reform":
                    validation = cls._validate_reform_locked(
                        case, run_name, time_path, allow_preceding_baseline=False
                    )
                    if validation:
                        cls._fail_quietly(case, run_name, validation["message"])
                        continue
                country, python_path, err = cls._resolve_country_env(case)
                if err:
                    cls._fail_quietly(case, run_name, err)
                    continue
                # Stamping rewrites run_meta.json and can fail on its own, so it is
                # inside the guard too: otherwise one unreadable run breaks out of
                # the drain and strands everything queued behind it.
                case.stamp_execution(run_name, time_path, country, "running")
            except (OSError, ValueError, KeyError, IndexError):
                cls._fail_quietly(case, run_name, "The run could not be started.")
                continue
            cls._launch(casename, run_name, time_path, python_path)
            return

    @staticmethod
    def _fail_quietly(case, run_name, message) -> None:
        """Mark a run failed, tolerating a meta file that cannot be written."""
        try:
            case.update_run_status(run_name, "failed", error=message)
        except (OSError, ValueError, KeyError, IndexError):
            pass

    # ── cancel ─────────────────────────────────────────────────────────────
    @classmethod
    def cancel(cls, casename: str, run_name: str) -> dict:
        with cls._lock:
            act = cls._active
            if act and act["casename"] == casename and act["run_name"] == run_name:
                act["cancelled"] = True
                runner = act["runner"]
                cancelled_active = True
            else:
                cancelled_active = False

        if cancelled_active:
            # Kill outside the lock: taskkill on a large Dask tree is synchronous and
            # would otherwise block every status poll and the install routes.
            try:
                if runner is not None:
                    runner.kill_tree()
            except OSError:
                pass
            # The supervision thread's finalize writes the terminal status.
            return {"status_code": "cancelled"}

        with cls._lock:
            for item in list(cls._queue):
                if item[0] == casename and item[1] == run_name:
                    cls._queue.remove(item)
                    # Dropping it from the queue is not enough; persist terminal
                    # cancellation so reloads never reconstruct it as queued.
                    try:
                        OGCoreCase(casename).update_run_status(
                            run_name, "failed", error="Cancelled by user."
                        )
                    except (OSError, ValueError, KeyError, IndexError):
                        # File.writeFile turns any write error into IndexError.
                        pass
                    return {"status_code": "cancelled"}

            return {
                "status_code": "error",
                "message": "That run is not running or queued.",
            }

    # ── startup housekeeping ───────────────────────────────────────────────
    @classmethod
    def reconcile_interrupted_runs(cls) -> None:
        """Repair runs left "running" or "queued" by a previous server exit.

        In-memory state is empty at startup, so a run still persisted as running has
        no supervisor behind it. Mark it failed, and kill its worker if that process
        somehow outlived the server (the machine never rebooted). A persisted queued
        run also has no in-memory FIFO entry after restart, so fail it truthfully.
        Created-but-never-started "pending" runs remain untouched. Best-effort,
        because startup housekeeping must never stop the app from serving.
        """
        try:
            case_dirs = [d for d in Config.OGC_CASES_DIR.iterdir() if d.is_dir()]
        except OSError:
            return
        for case_dir in case_dirs:
            case = OGCoreCase(case_dir.name)
            try:
                run_dirs = [d for d in case.res_path.iterdir() if d.is_dir()]
            except OSError:
                continue
            # Each run is handled on its own so one unreadable meta does not skip
            # the rest of the case.
            for run_dir in run_dirs:
                try:
                    meta = case.get_run_meta(run_dir.name)
                    if (
                        not isinstance(meta, dict)
                        or meta.get("status") not in ("running", "queued")
                    ):
                        continue
                    was_running = meta.get("status") == "running"
                    if was_running:
                        kill_worker_tree(meta.get("pid"), run_dir)
                    case.update_run_status(
                        run_dir.name, "failed",
                        error=(
                            "Run was interrupted by an application restart."
                            if was_running
                            else "Queued run was interrupted by an application restart before it started."
                        ),
                    )
                except (OSError, ValueError, KeyError, IndexError):
                    continue

    # ── shutdown ───────────────────────────────────────────────────────────
    @classmethod
    def stop_active(cls) -> bool:
        """Stop the running worker so a server shutdown does not orphan its tree.

        Marks the run cancelled and kills the worker. If the supervision thread still
        gets to finish it will record the failure; on a hard exit the persisted
        "running" status is repaired by reconcile on the next start. Returns True if
        a run was active.
        """
        with cls._lock:
            act = cls._active
            if act is None:
                return False
            act["cancelled"] = True
            runner = act["runner"]
        try:
            if runner is not None:
                runner.kill_tree()
        except OSError:
            pass
        return True

    # ── live view ──────────────────────────────────────────────────────────
    @classmethod
    def get_live(cls, casename: str, run_name: str) -> dict | None:
        with cls._lock:
            act = cls._active
            if act and act["casename"] == casename and act["run_name"] == run_name:
                runner = act["runner"]
                queued = False
            else:
                queue_position = next(
                    (
                        index
                        for index, q in enumerate(cls._queue, start=1)
                        if q[0] == casename and q[1] == run_name
                    ),
                    None,
                )
                if queue_position is None:
                    return None
                runner = None
                queued = True
            if not queued:
                queue_position = None
            queue_length = len(cls._queue)

        stage_label = None
        if runner is not None:
            status = cls._read_status(cls._run_dir(casename, run_name))
            if status is not None:
                stage_label = status.get("label")

        return {
            "stage_label": stage_label,
            "iteration": runner.iteration if runner is not None else None,
            "log_tail": runner.log_tail() if runner is not None else [],
            "queued": queued,
            "queue_position": queue_position,
            "queue_length": queue_length,
        }

    @classmethod
    def get_queue_snapshot(cls, casename: str) -> dict:
        """Read-only FIFO view sufficient to reconstruct the Run page."""
        with cls._lock:
            active = None
            if cls._active and cls._active["casename"] == casename:
                active = {
                    "casename": casename,
                    "run_name": cls._active["run_name"],
                    "state": "running",
                }
            queued = [
                {
                    "casename": queued_case,
                    "run_name": queued_run,
                    "state": "queued",
                    "queue_position": index,
                    "time_path": time_path,
                }
                for index, (queued_case, queued_run, time_path)
                in enumerate(cls._queue, start=1)
                if queued_case == casename
            ]
        return {"active": active, "queued": queued}
