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
        # Preserve the original install date across an update (re-running over an
        # existing calibration); only a first install sets installed_at.
        existing = CalibrationRegistry.get(country_id)
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
            "installed_at": existing.get("installed_at", now) if existing else now,
            "last_checked_at": now,
        }
        if existing:
            record["last_updated_at"] = now
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
                cls._persist(snapshot)

    @classmethod
    def _run(cls, install_id, country_id, source_type, country_name, work_fn):
        """Thread target: run work_fn(progress, log) -> result, finalize, release."""
        progress, log = cls._callbacks(install_id)
        try:
            result = work_fn(progress, log)
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

    @classmethod
    def _launch(cls, *, country_id, country_name, source_type, work_fn):
        # Check-and-claim the country under one lock so two concurrent requests for
        # the same country cannot both start and clone into the same directory.
        # Returns None if an install for this country is already running.
        with cls._lock:
            if country_id in cls._active_by_country:
                return None
            install_id = cls._new_install_id()  # RLock is reentrant
            job = cls._init_job(
                install_id, country_id=country_id, country_name=country_name,
                source_type=source_type,
            )
            cls._jobs[install_id] = job
            cls._active_by_country[country_id] = install_id
            initial = dict(job)  # snapshot before the thread can advance it
        cls._persist(initial)

        thread = CustomThread(
            target=cls._run,
            args=(install_id, country_id, source_type, country_name, work_fn),
        )
        thread.daemon = True
        thread.start()
        return initial

    # ── public entry points ──────────────────────────────────────────────────
    @classmethod
    def start_install(cls, *, source_type, country_id, country_name, repo_name,
                      dest_parent, catalog_key=None, repo_url=None, branch=None,
                      package_name=None):
        """Start a catalog or repo_url install. Returns the initial job dict."""
        def work(progress, log):
            return Installer.run_installer(
                source_type=source_type, repo_name=repo_name,
                dest_parent=dest_parent, catalog_key=catalog_key,
                repo_url=repo_url, branch=branch, package_name=package_name,
                log=log, progress=progress,
            )

        return cls._launch(
            country_id=country_id, country_name=country_name,
            source_type=source_type, work_fn=work,
        )

    @classmethod
    def start_local_register(cls, *, country_id, country_name, local_path,
                             package_name=None, run_uv_sync=True):
        """Start a local-path registration. Returns the initial job dict."""
        def work(progress, log):
            return Installer.register_local(
                local_path=local_path, package_name=package_name,
                run_uv_sync=run_uv_sync, log=log, progress=progress,
            )

        return cls._launch(
            country_id=country_id, country_name=country_name,
            source_type="local_path", work_fn=work,
        )
