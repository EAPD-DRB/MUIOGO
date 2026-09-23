"""Post-run hook: a finished CLEWs solve triggers the OG-CLEWS link, and the OG
results are registered in the case's view/resData.json for the UI.

Called by ``DataFile.run`` after a successful solve. The link runs in ITS OWN
venv (oglink/.venv) as a subprocess (``python -m oglink run ...``); this
module never imports oglink or ogcore -- that is the design boundary, in both
directions.

The hook is opt-in per case and silent by default:
  * no ``<case>/oglink/hook.json`` -> no-op (a CLEWs-only user is unaffected);
  * the case is an OG-link COPY (``oglink/created.json``) -> no-op: that solve
    was driven BY the link or /oglink/applyPatch, and running the link again
    would recurse;
  * ``$MUIOGO_OGLINK_HOOK=0`` -> no-op (global off switch);
  * the finished caserun IS the configured base -> no-op (nothing to compare);
  * the link env cannot be resolved -> no-op with a one-line logged reason.
Every no-op returns a small ``{"status": "skipped", "reason": ...}`` so the
/run response says what happened; only actually-attempted link runs are
registered in resData.json (successes AND failures, so the UI can show both).

``hook.json``:
    {"enabled": true, "experiment": "coupled", "base_caserun": "Base_v9",
     "country": "phl", "workers": 7, "timeout_s": 21600,
     "out": null, "extra_args": []}
"""
import logging
import os
import re
import subprocess
import threading
from datetime import datetime, timezone, UTC
from pathlib import Path

from Classes.Base import Config
from Classes.Base.FileClass import File

logger = logging.getLogger(__name__)

_OFF_VALUES = {"0", "off", "false", "no"}
_REGISTER_LOCK = threading.Lock()


class PostRunHook:

    # ── environment resolution (explicit, no PATH guessing) ──────────────────
    @staticmethod
    def link_python():
        """The linker's own interpreter: $OGLINK_PYTHON, else the venv under
        $OGLINK_HOME, else this checkout's oglink/.venv. None if that
        environment has not been built (the hook then no-ops)."""
        explicit = os.environ.get("OGLINK_PYTHON")
        if explicit:
            return explicit if Path(explicit).is_file() else None
        home = Path(os.environ.get("OGLINK_HOME") or Config.OGLINK_HOME_DIR)
        candidate = Config.venv_python_path(home / ".venv")
        return str(candidate) if candidate.is_file() else None

    @staticmethod
    def link_home(python_path):
        """The link checkout the interpreter belongs to (the subprocess cwd, so
        the link's own ./og_model_registry.json and countries JSON resolve):
        $OGLINK_HOME, else the dir holding the interpreter's .venv. None
        when underivable (an interpreter outside a .venv needs the env var)."""
        if os.environ.get("OGLINK_HOME"):
            return os.environ["OGLINK_HOME"]
        # abspath, NOT resolve(): a uv venv's python is a symlink into the uv
        # python store; following it would walk the store, never the .venv.
        for parent in Path(os.path.abspath(python_path)).parents:
            if parent.name == ".venv":
                return str(parent.parent)
        return None

    @classmethod
    def status(cls):
        """Is the link usable from here? {installed, python, home, reason} --
        the capability check the UI (and MUIOGO-AI) reads before offering a
        coupled run."""
        python = cls.link_python()
        if python is None:
            return {"installed": False, "python": None, "home": None,
                    "reason": "the OG-CLEWS linker environment is not built: no "
                              f"venv at {Config.OGLINK_HOME_DIR / '.venv'} (and no "
                              "$OGLINK_PYTHON / $OGLINK_HOME override)"}
        home = cls.link_home(python)
        if home is None:
            return {"installed": False, "python": python, "home": None,
                    "reason": "interpreter is not inside a .venv; set "
                              "$OGLINK_HOME to the linker folder"}
        return {"installed": True, "python": python, "home": home, "reason": None}

    @classmethod
    def models_check(cls, python, home):
        """Ask the installed link which OG models it has registered -- the
        second half of the capability check (a link with no registered model
        cannot run a coupled experiment)."""
        try:
            out = subprocess.run([python, "-m", "oglink", "models", "list"],
                                 cwd=home, capture_output=True, text=True,
                                 timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"models_registered": False,
                    "models_output": f"{type(exc).__name__}: {exc}"}
        ok = out.returncode == 0
        return {"models_registered": bool(ok and "[x]" in out.stdout),
                "models_output": (out.stdout if ok else out.stderr).strip()[-1000:]}

    # ── the hook ──────────────────────────────────────────────────────────────
    @classmethod
    def after_run(cls, case, caserun):
        """Run the link for a finished (case, caserun) solve. Returns a summary
        dict for the /run response, or None when the hook does not apply at
        all. NEVER raises: any surprise is caught, logged, and reported in the
        summary -- the CLEWs run's own result must not be affected."""
        try:
            return cls._after_run(case, caserun)
        except Exception as exc:  # noqa: BLE001 -- containment is the contract
            logger.warning("oglink hook: unexpected error (CLEWs run unaffected): %s", exc)
            return {"status": "error", "reason": f"{type(exc).__name__}: {exc}"}

    @classmethod
    def _after_run(cls, case, caserun):
        def skip(reason, level=logging.INFO):
            logger.log(level, "oglink hook: skipped for %s/%s: %s", case, caserun, reason)
            return {"status": "skipped", "reason": reason}

        if os.environ.get("MUIOGO_OGLINK_HOOK", "").lower() in _OFF_VALUES:
            return skip("disabled by $MUIOGO_OGLINK_HOOK")
        case_dir = Path(Config.DATA_STORAGE, case)
        if (case_dir / "oglink" / "created.json").is_file():
            return skip("case is an OG-link copy; its solves are link-driven")
        cfg_path = case_dir / "oglink" / "hook.json"
        if not cfg_path.is_file():
            return None  # not configured: fully silent no-op
        cfg = File.readFile(cfg_path)
        if not cfg.get("enabled", True):
            return skip("hook.json has enabled=false")
        experiment = cfg.get("experiment")
        base_caserun = cfg.get("base_caserun")
        if not experiment or not base_caserun:
            return skip("hook.json must set 'experiment' and 'base_caserun'")
        if caserun == base_caserun:
            return skip("finished caserun is the configured base; nothing to compare")
        base_csv = case_dir / "res" / base_caserun / "csv"
        reform_csv = case_dir / "res" / caserun / "csv"
        if not base_csv.is_dir():
            return skip(f"base caserun csv missing ({base_csv}); solve "
                        f"{base_caserun!r} first")
        python = cls.link_python()
        if python is None:
            return skip("the OG-CLEWS linker environment is not built (no venv "
                        f"at {Config.OGLINK_HOME_DIR / '.venv'})")
        home = cls.link_home(python)
        if home is None:
            return skip("cannot derive the link checkout from the interpreter; "
                        "set $OGLINK_HOME")

        # Out of the DataStorage tree (Config's own rule): run outputs are big,
        # and the link's OG-baseline cache lives under --out, so a stable
        # per-case root shares that cache across this case's caseruns.
        out_dir = cfg.get("out") or str(Config.OGLINK_RUNS_DIR / case)
        os.makedirs(out_dir, exist_ok=True)
        cmd = [python, "-m", "oglink", "run", experiment,
               "--clews-base", str(base_csv), "--clews-reform", str(reform_csv),
               "--clews-run", str(case_dir / "res" / caserun),
               "--out", out_dir, "--workers", str(cfg.get("workers", 7)),
               "--no-progress"]
        if cfg.get("country"):
            cmd += ["--country", str(cfg["country"])]
        cmd += [str(a) for a in cfg.get("extra_args", [])]

        timeout = int(cfg.get("timeout_s", 21600))
        started = datetime.now(UTC)
        logger.info("oglink hook: running %s", " ".join(cmd))
        # Own process group + kill the WHOLE TREE on timeout: the link spawns
        # the OG solver as a grandchild, which a plain timeout-kill would
        # orphan (the same lesson clews_driver.run_caserun learned live).
        # start_new_session is POSIX-only (silently ignored on Windows, where
        # taskkill /T kills the tree by pid instead).
        proc = subprocess.Popen(cmd, cwd=home,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True)
        try:
            out, err = proc.communicate(timeout=timeout)
            status = "success" if proc.returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            cls._kill_tree(proc)
            out, err = "", f"timed out after {timeout}s; process tree killed"
            status = "timeout"

        run_dir = Path(out_dir) / experiment
        manifest = None
        match = re.search(r"Wrote run manifest: (.+)", out or "")
        if match:
            manifest = match.group(1).strip()
        elif (run_dir / "oglink_manifest.json").is_file():
            manifest = str(run_dir / "oglink_manifest.json")

        entry = {
            "case": case, "caserun": caserun, "experiment": experiment,
            "status": status, "returncode": proc.returncode,
            "out_dir": str(run_dir), "manifest": manifest,
            "macro_table": (str(run_dir / "macro_table.csv")
                            if (run_dir / "macro_table.csv").is_file() else None),
            "deck": (str(run_dir / "index.html")
                     if (run_dir / "index.html").is_file() else None),
            "clews_base": str(base_csv), "clews_reform": str(reform_csv),
            "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "elapsed_s": round((datetime.now(UTC) - started).total_seconds(), 1),
            "stdout_tail": (out or "")[-2000:], "stderr_tail": (err or "")[-2000:],
        }
        cls.register(case, entry)
        logger.info("oglink hook: %s for %s/%s in %ss", status, case, caserun,
                    entry["elapsed_s"])
        summary = {k: entry[k] for k in ("status", "experiment", "out_dir",
                                         "manifest", "elapsed_s")}
        if status != "success":
            summary["stderr_tail"] = entry["stderr_tail"][-400:]
        return summary

    @staticmethod
    def _kill_tree(proc):
        """Terminate the subprocess AND its descendants, on both platforms.
        POSIX: signal the process group (we started a new session). Windows:
        os.killpg does not exist; taskkill /T walks the tree by pid."""
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True)
            return
        os.killpg(os.getpgid(proc.pid), 15)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), 9)

    # ── registration (the same read-merge-write idiom as /updateData) ─────────
    @staticmethod
    def register(case, entry):
        """Record the run under an additive 'oglink-runs' key in the case's
        view/resData.json; existing readers only touch 'osy-cases'. ONE entry
        per experiment, replaced on re-run: the link overwrites
        <out>/<experiment>/ each time, so an older entry would point at
        another caserun's results."""
        path = Path(Config.DATA_STORAGE, case, "view", "resData.json")
        with _REGISTER_LOCK:
            res_data = File.readFile(path)
            runs = res_data.setdefault("oglink-runs", [])
            runs[:] = [r for r in runs if r.get("experiment") != entry["experiment"]]
            runs.append(entry)
            File.writeFile(res_data, path)
