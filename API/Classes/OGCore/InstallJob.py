"""Background install/registration jobs for OG calibrations.

An install (clone + uv sync + verify) takes minutes, so the route starts a job and
returns immediately; the frontend polls getInstallStatus. Jobs run in a CustomThread.
In-memory job state is authoritative while a job runs (single-process waitress); it is
also persisted to disk at stage boundaries and on completion for durable status reads.

On success the finished environment is written to the installed registry, which is the
hand-off the run layer later uses (python_path).
"""
import threading
from datetime import date, datetime, timezone

from Classes.Base import Config
from Classes.Base.CustomThreadClass import CustomThread
from Classes.Base.FileClass import File
from Classes.OGCore.CalibrationRegistry import CalibrationRegistry
from Classes.OGCore.Installer import Installer, InstallerError

_LOG_TAIL_MAX = 50

# A label for each install_stage, shown in the UI progress line.
_STAGE_LABELS = {
    "preflight": "Preparing install",
    "install_uv": "Installing uv",
    "clone": "Cloning the repository",
    "pull": "Updating the repository",
    "uv_sync": "Installing dependencies with uv",
    "verify_import": "Verifying the model imports",
    "register": "Recording the installed calibration",
    "complete": "Done",
}


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class InstallJob:
    _lock = threading.RLock()
    _jobs = {}               # install_id -> job dict
    _active_by_country = {}  # country_id -> install_id (only while running)
    _cancel_by_id = {}       # install_id -> threading.Event (only while running)
    _shutting_down = False   # set by cancel_all so no new install starts during shutdown

    # ── id + persistence ─────────────────────────────────────────────────────
    @classmethod
    def _new_install_id(cls):
        Config.OGC_INSTALL_JOBS_DIR.mkdir(parents=True, exist_ok=True)
        prefix = f"install_{date.today().strftime('%Y_%m_%d')}_"
        with cls._lock:
            existing = {p.stem for p in Config.OGC_INSTALL_JOBS_DIR.glob(prefix + "*.json")}
            existing.update(iid for iid in cls._jobs if iid.startswith(prefix))
            n = 1
            while f"{prefix}{n:03d}" in existing:
                n += 1
            return f"{prefix}{n:03d}"

    @classmethod
    def _persist(cls, job):
        try:
            Config.OGC_INSTALL_JOBS_DIR.mkdir(parents=True, exist_ok=True)
            File.writeFile(job, Config.OGC_INSTALL_JOBS_DIR / f"{job['install_id']}.json")
        except (OSError, IndexError):
            # Status is still served from memory; a failed persist is non-fatal.
            pass

    # ── status reads ─────────────────────────────────────────────────────────
    @classmethod
    def get_status(cls, install_id):
        with cls._lock:
            job = cls._jobs.get(install_id)
            if job is not None:
                return dict(job)
        path = Config.OGC_INSTALL_JOBS_DIR / f"{install_id}.json"
        if path.exists():
            try:
                return File.readFile(path)
            except (OSError, ValueError, IndexError):
                return None
        return None

    @classmethod
    def is_country_active(cls, country_id):
        with cls._lock:
            return country_id in cls._active_by_country

    # ── startup housekeeping ─────────────────────────────────────────────────────
    @classmethod
    def reconcile_interrupted_jobs(cls):
        """Fail any job left mid-flight by a previous server restart.

        A job persisted as installing/checking with no live thread behind it (always
        true right after a restart) would otherwise read as installing forever. Mark
        such jobs, and the registry records they left behind, as failed, preserving a
        still-usable install. Best-effort: startup housekeeping must never crash the app.
        """
        # Only genuinely in-flight states are "interrupted". An allowlist, not "everything
        # non-terminal", so a healthy idle record (e.g. install_state "update_available"
        # from a refresh check) is never rewritten with a false restart error.
        transient = {"installing", "checking"}
        try:
            for record in CalibrationRegistry.list_all():
                country_id = record.get("country_id")
                if (country_id and record.get("install_state") in transient
                        and not cls.is_country_active(country_id)):
                    cls._mark_registry_failed(country_id, "Interrupted by a server restart.")
        except Exception:
            pass
        try:
            job_files = list(Config.OGC_INSTALL_JOBS_DIR.glob("*.json"))
        except OSError:
            job_files = []
        for path in job_files:
            try:
                job = File.readFile(path)
                if (not isinstance(job, dict)
                        or job.get("install_state") not in transient
                        or cls.is_country_active(job.get("country_id"))):
                    continue
                job.update(
                    install_state="failed",
                    progress_label="Install failed",
                    error="Interrupted by a server restart.",
                    updated_at=_now_iso(),
                )
                cls._persist(job)
            except (OSError, ValueError, IndexError):
                continue

    # ── job lifecycle ────────────────────────────────────────────────────────
    @classmethod
    def _init_job(cls, install_id, *, country_id, country_name, source_type):
        return {
            "install_id": install_id,
            "country_id": country_id,
            "country_name": country_name,
            "source_type": source_type,
            "install_state": "checking",
            "install_stage": "preflight",
            "progress_label": _STAGE_LABELS["preflight"],
            "local_path": None,
            "log_tail": [],
            "error": None,
            "started_at": _now_iso(),
            "updated_at": _now_iso(),
        }

    @classmethod
    def _callbacks(cls, install_id):
        """progress(stage, label) and log(line) closures bound to a job."""
        def progress(stage, label=None):
            with cls._lock:
                job = cls._jobs.get(install_id)
                if job is None:
                    return
                job["install_stage"] = stage
                job["progress_label"] = label or _STAGE_LABELS.get(stage, stage)
                if stage not in ("preflight", "complete"):
                    job["install_state"] = "installing"
                job["updated_at"] = _now_iso()
                snapshot = dict(job)
            cls._persist(snapshot)  # persist on stage boundaries only

        def log(line):
            with cls._lock:
                job = cls._jobs.get(install_id)
                if job is None:
                    return
                tail = job["log_tail"]
                tail.append(line)
                if len(tail) > _LOG_TAIL_MAX:
                    del tail[: len(tail) - _LOG_TAIL_MAX]
                job["updated_at"] = _now_iso()

        return progress, log

    @classmethod
    def _finalize_success(cls, install_id, *, source_type, country_id,
                          country_name, result):
        now = _now_iso()
        # Preserve the original install date across an update. A prior *successful*
        # install is the one that recorded installed_at; the installing/failed record
        # now written at job start is not a prior install and must not be counted as an
        # update. Rebuilding the record from scratch also drops any stale last_error.
        existing = CalibrationRegistry.get(country_id)
        prior_installed_at = existing.get("installed_at") if existing else None
        record = {
            "country_id": country_id,
            "country_name": country_name,
            "source_type": source_type,
            "local_path": result["local_path"],
            "venv_path": result["venv_path"],
            "python_path": result["python_path"],
            "package_name": result["package_name"],
            "repo_url": result.get("repo_url"),
            "commit_sha": result.get("commit_sha"),
            "install_state": "installed",
            "install_id": install_id,
            "installed_at": prior_installed_at or now,
            "last_checked_at": now,
        }
        if prior_installed_at:
            record["last_updated_at"] = now
        # Not best-effort: this record is the hand-off the run layer needs (python_path).
        # If it cannot be persisted, _run treats the job as failed rather than reporting
        # a success the run layer could never act on.
        CalibrationRegistry.upsert(record)
        with cls._lock:
            job = cls._jobs.get(install_id)
            if job is not None:
                job.update(
                    install_state="installed",
                    install_stage="complete",
                    progress_label=_STAGE_LABELS["complete"],
                    local_path=result["local_path"],
                    error=None,
                    updated_at=_now_iso(),
                )
                snapshot = dict(job)
                cls._persist(snapshot)

    @classmethod
    def _finalize_failure(cls, install_id, message, local_path=None):
        country_id = None
        snapshot = None
        with cls._lock:
            job = cls._jobs.get(install_id)
            if job is not None:
                job.update(
                    install_state="failed",
                    progress_label="Install failed",
                    error=message,
                    updated_at=_now_iso(),
                )
                if local_path:
                    job["local_path"] = local_path
                snapshot = dict(job)
                country_id = job["country_id"]
        if snapshot is not None:
            cls._persist(snapshot)
        if country_id is not None:
            cls._mark_registry_failed(country_id, message)

    @classmethod
    def _mark_registry_failed(cls, country_id, message):
        """Reflect a failed job in the installed registry, so any client sees it.

        A failed *update* must not hide a still-working install: if the record still
        points at an installed venv, keep it installed and note the failure in
        last_error; only a country with no usable install is marked failed. Best-effort,
        because recording status must not mask the failure already being handled.
        """
        try:
            record = CalibrationRegistry.get(country_id)
            if record and record.get("venv_path"):
                CalibrationRegistry.update_fields(
                    country_id, install_state="installed", last_error=message)
            else:
                CalibrationRegistry.update_fields(
                    country_id, install_state="failed", last_error=message)
        except Exception:
            # Best-effort: recording status must never mask the failure being handled.
            pass

    @classmethod
    def _record_started(cls, *, country_id, country_name, source_type, install_id):
        """Put the job in the installed registry the moment it starts.

        This is what lets any client, not just the one that launched it, see the country
        as installing and reach the running job by id after a reload. Patch an existing
        record so an update keeps venv_path and friends; create a minimal one otherwise.
        Best-effort: failing to record status must not abort a real install.
        """
        try:
            patched = CalibrationRegistry.update_fields(
                country_id, install_state="installing", install_id=install_id)
            if patched is None:
                CalibrationRegistry.upsert({
                    "country_id": country_id,
                    "country_name": country_name,
                    "source_type": source_type,
                    "install_state": "installing",
                    "install_id": install_id,
                })
        except Exception:
            # Best-effort: recording status must never abort a real install, and must
            # not leave the country claimed (this runs before the worker thread starts).
            pass

    @classmethod
    def _run(cls, install_id, country_id, source_type, country_name, work_fn, cancel_event):
        """Thread target: run work_fn(progress, log, cancel) -> result, finalize, release."""
        progress, log = cls._callbacks(install_id)
        try:
            result = work_fn(progress, log, cancel_event)
            if result.get("ok"):
                cls._finalize_success(
                    install_id, source_type=source_type, country_id=country_id,
                    country_name=country_name, result=result,
                )
            else:
                cls._finalize_failure(
                    install_id, result.get("error") or "Install failed.",
                    local_path=result.get("local_path"),
                )
        except InstallerError as exc:
            cls._finalize_failure(install_id, str(exc))
        except Exception as exc:  # any unexpected crash still ends the job cleanly
            cls._finalize_failure(install_id, f"Unexpected error: {exc}")
        finally:
            with cls._lock:
                if cls._active_by_country.get(country_id) == install_id:
                    cls._active_by_country.pop(country_id, None)
                cls._cancel_by_id.pop(install_id, None)

    @classmethod
    def _launch(cls, *, country_id, country_name, source_type, work_fn):
        # Check-and-claim the country under one lock so two concurrent requests for
        # the same country cannot both start and clone into the same directory.
        # Returns None if an install for this country is already running, or if the
        # server is shutting down (so a late request cannot orphan a fresh process tree).
        with cls._lock:
            if cls._shutting_down:
                return None
            if country_id in cls._active_by_country:
                return None
            install_id = cls._new_install_id()  # RLock is reentrant
            job = cls._init_job(
                install_id, country_id=country_id, country_name=country_name,
                source_type=source_type,
            )
            cls._jobs[install_id] = job
            cls._active_by_country[country_id] = install_id
            cancel_event = threading.Event()
            cls._cancel_by_id[install_id] = cancel_event
            initial = dict(job)  # snapshot before the thread can advance it
        cls._persist(initial)
        cls._record_started(
            country_id=country_id, country_name=country_name,
            source_type=source_type, install_id=install_id,
        )

        thread = CustomThread(
            target=cls._run,
            args=(install_id, country_id, source_type, country_name, work_fn,
                  cancel_event),
        )
        thread.daemon = True
        thread.start()
        return initial

    @classmethod
    def cancel(cls, install_id):
        """Ask a running job to stop. Returns True if one was signalled, else False.

        The worker sees the event, kills the install's process tree, and finalizes as a
        failure with 'Cancelled by user.' (a cancelled update keeps its working install).
        """
        with cls._lock:
            event = cls._cancel_by_id.get(install_id)
        if event is None:
            return False
        event.set()
        return True

    @classmethod
    def active_count(cls):
        """How many installs are running in this process right now."""
        with cls._lock:
            return len(cls._active_by_country)

    @classmethod
    def cancel_all(cls):
        """Signal every running install to stop. Returns the install_ids signalled.

        For server shutdown: installs run in their own process group so cancel can
        tree-kill them, which also means a plain server stop would orphan them. Setting
        each cancel event lets the running supervisors tear their trees down and finalize
        as failures, exactly like a user cancel. Idempotent: a second call after the jobs
        clear sees an empty map and returns nothing.

        Also latches a shutting-down flag (under the same lock as the snapshot) so a
        request racing in on another thread cannot start a new, unsignalled install after
        this snapshot and leave its process tree orphaned.
        """
        with cls._lock:
            cls._shutting_down = True
            events = list(cls._cancel_by_id.items())
        for _install_id, event in events:
            event.set()
        return [install_id for install_id, _ in events]

    # ── public entry points ──────────────────────────────────────────────────
    @classmethod
    def start_install(cls, *, source_type, country_id, country_name, repo_name,
                      dest_parent, catalog_key=None, repo_url=None, branch=None,
                      package_name=None, record_as=None):
        """Start a catalog or repo_url install. Returns the initial job dict.

        record_as: source_type to write on the registry record when it differs from
        the install mechanism. An update of a locally-registered clone runs through
        the repo_url installer but must stay a local_path record, so the same
        safety checks apply to its next update.
        """
        def work(progress, log, cancel):
            return Installer.run_installer(
                source_type=source_type, repo_name=repo_name,
                dest_parent=dest_parent, catalog_key=catalog_key,
                repo_url=repo_url, branch=branch, package_name=package_name,
                log=log, progress=progress, cancel=cancel,
            )

        return cls._launch(
            country_id=country_id, country_name=country_name,
            source_type=record_as or source_type, work_fn=work,
        )

    @classmethod
    def start_local_register(cls, *, country_id, country_name, local_path,
                             package_name=None, run_uv_sync=True):
        """Start a local-path registration. Returns the initial job dict."""
        def work(progress, log, cancel):
            return Installer.register_local(
                local_path=local_path, package_name=package_name,
                run_uv_sync=run_uv_sync, log=log, progress=progress, cancel=cancel,
            )

        return cls._launch(
            country_id=country_id, country_name=country_name,
            source_type="local_path", work_fn=work,
        )
