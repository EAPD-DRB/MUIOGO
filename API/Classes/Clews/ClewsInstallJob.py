"""Background CLEWs country install jobs.

Downloading and importing a country's case archives can take a while on a slow
connection, so the route starts a job and returns; the client polls
getClewsInstallStatus. Same shape as the OG InstallJob, but deliberately lighter:
a CLEWs install is pure Python (download, hash, unzip) -- no detached process
trees, so cancellation is just an Event the download loop checks between chunks.

In-flight installs never touch the case registry: the registry is reconciled from
what is actually on disk, and a mid-install record with no case directory yet
would be dropped by any concurrent reconcile. The job file is the progress record;
the case appears in the registry when it lands (the job's success path reconciles).
"""
import shutil
import threading
from datetime import date, datetime, timezone

from Classes.Base import Config
from Classes.Base.CustomThreadClass import CustomThread
from Classes.Base.FileClass import File
from Classes.Clews.ClewsInstaller import ClewsInstaller
from Classes.Clews.CountryManifest import InstallCancelled, ManifestError
from Classes.Clews.CountryRegistry import CountryRegistry

_LOG_TAIL_MAX = 50

_STAGE_LABELS = {
    "preflight": "Preparing install",
    "manifest": "Reading the country manifest",
    "checksums": "Reading the published checksums",
    "download": "Downloading case archives",
    "verify": "Verifying checksums",
    "import": "Importing cases",
    "complete": "Done",
}


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ClewsInstallJob:
    _lock = threading.RLock()
    _jobs = {}              # install_id -> job dict
    _active_by_key = {}     # country key (iso3 or source label) -> install_id
    _cancel_by_id = {}      # install_id -> threading.Event
    _shutting_down = False

    # ── id + persistence ─────────────────────────────────────────────────────
    @classmethod
    def _new_install_id(cls):
        Config.CLEWS_INSTALL_JOBS_DIR.mkdir(parents=True, exist_ok=True)
        prefix = f"clews_{date.today().strftime('%Y_%m_%d')}_"
        with cls._lock:
            existing = {p.stem for p in Config.CLEWS_INSTALL_JOBS_DIR.glob(prefix + "*.json")}
            existing.update(iid for iid in cls._jobs if iid.startswith(prefix))
            n = 1
            while f"{prefix}{n:03d}" in existing:
                n += 1
            return f"{prefix}{n:03d}"

    @classmethod
    def _persist(cls, job):
        try:
            Config.CLEWS_INSTALL_JOBS_DIR.mkdir(parents=True, exist_ok=True)
            File.writeFile(job, Config.CLEWS_INSTALL_JOBS_DIR / f"{job['install_id']}.json")
        except (OSError, IndexError):
            pass  # status is still served from memory

    # ── status reads ─────────────────────────────────────────────────────────
    @classmethod
    def get_status(cls, install_id):
        with cls._lock:
            job = cls._jobs.get(install_id)
            if job is not None:
                return dict(job)
        path = Config.CLEWS_INSTALL_JOBS_DIR / f"{install_id}.json"
        if path.exists():
            try:
                return File.readFile(path)
            except (OSError, ValueError, IndexError):
                return None
        return None

    @classmethod
    def is_key_active(cls, key):
        with cls._lock:
            return key in cls._active_by_key

    @classmethod
    def active_count(cls):
        with cls._lock:
            return len(cls._active_by_key)

    # ── startup housekeeping ─────────────────────────────────────────────────
    @classmethod
    def reconcile_interrupted_jobs(cls):
        """Fail any job file left installing by a previous restart. Best-effort."""
        try:
            job_files = list(Config.CLEWS_INSTALL_JOBS_DIR.glob("*.json"))
        except OSError:
            job_files = []
        for path in job_files:
            try:
                job = File.readFile(path)
                if (not isinstance(job, dict)
                        or job.get("install_state") not in ("installing", "checking")
                        or cls.is_key_active(job.get("country_key"))):
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

    # ── lifecycle ────────────────────────────────────────────────────────────
    @classmethod
    def _callbacks(cls, install_id):
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
            cls._persist(snapshot)

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
    def _finalize(cls, install_id, *, state, results=None, error=None):
        with cls._lock:
            job = cls._jobs.get(install_id)
            if job is None:
                return
            job.update(
                install_state=state,
                install_stage="complete",
                progress_label=(_STAGE_LABELS["complete"] if state == "installed"
                                else "Install failed"),
                error=error,
                updated_at=_now_iso(),
            )
            if results is not None:
                job["results"] = results
            snapshot = dict(job)
        cls._persist(snapshot)

    @classmethod
    def _run(cls, install_id, key, work_fn, cancel_event, staging_dir):
        progress, log = cls._callbacks(install_id)
        try:
            result = work_fn(progress, log, cancel_event)
            if result.get("ok"):
                # Index the freshly landed sidecars right away, so the installed
                # list is current without waiting for the next read's reconcile.
                try:
                    CountryRegistry.reconcile()
                except Exception:
                    pass  # the next reconcile-on-read picks them up
                cls._finalize(install_id, state="installed",
                              results=result.get("results"))
            else:
                cls._finalize(install_id, state="failed",
                              results=result.get("results"),
                              error=result.get("error") or "Install failed.")
        except InstallCancelled:
            shutil.rmtree(staging_dir, ignore_errors=True)
            cls._finalize(install_id, state="failed", error="Cancelled by user.")
        except ManifestError as exc:
            cls._finalize(install_id, state="failed", error=str(exc))
        except Exception as exc:  # any unexpected crash still ends the job cleanly
            cls._finalize(install_id, state="failed", error=f"Unexpected error: {exc}")
        finally:
            with cls._lock:
                if cls._active_by_key.get(key) == install_id:
                    cls._active_by_key.pop(key, None)
                cls._cancel_by_id.pop(install_id, None)

    # ── public entry point ───────────────────────────────────────────────────
    @classmethod
    def start_install(cls, *, source, country_key, vintage_id=None, casenames=None):
        """Launch a country install. Returns the initial job dict, or None if an
        install for this country is already running (or the server is stopping)."""
        with cls._lock:
            if cls._shutting_down:
                return None
            if country_key in cls._active_by_key:
                return None
            install_id = cls._new_install_id()
            job = {
                "install_id": install_id,
                "country_key": country_key,
                "source": source.describe(),
                "vintage": vintage_id,
                "cases_requested": list(casenames) if casenames else None,
                "install_state": "checking",
                "install_stage": "preflight",
                "progress_label": _STAGE_LABELS["preflight"],
                "log_tail": [],
                "results": None,
                "error": None,
                "started_at": _now_iso(),
                "updated_at": _now_iso(),
            }
            cls._jobs[install_id] = job
            cls._active_by_key[country_key] = install_id
            cancel_event = threading.Event()
            cls._cancel_by_id[install_id] = cancel_event
            initial = dict(job)
        cls._persist(initial)

        staging_dir = str(Config.CLEWS_DOWNLOADS_DIR / install_id)

        def work(progress, log, cancel):
            return ClewsInstaller.run_install(
                source=source, vintage_id=vintage_id, casenames=casenames,
                staging_dir=staging_dir, progress=progress, log=log, cancel=cancel,
            )

        thread = CustomThread(
            target=cls._run,
            args=(install_id, country_key, work, cancel_event, staging_dir),
        )
        thread.daemon = True
        thread.start()
        return initial

    @classmethod
    def cancel(cls, install_id):
        """Ask a running job to stop. True if one was signalled."""
        with cls._lock:
            event = cls._cancel_by_id.get(install_id)
        if event is None:
            return False
        event.set()
        return True

    @classmethod
    def cancel_all(cls):
        """Signal every running install to stop (server shutdown). Idempotent."""
        with cls._lock:
            cls._shutting_down = True
            events = list(cls._cancel_by_id.items())
        for _install_id, event in events:
            event.set()
        return [install_id for install_id, _ in events]
