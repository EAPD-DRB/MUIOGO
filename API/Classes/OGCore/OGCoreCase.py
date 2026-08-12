"""On-disk CRUD for OG-Core cases and runs. Does not run the model or import
ogcore; runs happen in a separate environment via the worker. Parameters live
per run: a baseline and a reform are the same model with different params."""

from __future__ import annotations

import json
import hashlib
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from Classes.Base import Config
from Classes.Base.FileClass import File
from Classes.OGCore.CalibrationRegistry import CalibrationRegistry

logger = logging.getLogger(__name__)

# A case/run name becomes a directory, so it has to be a safe path component.
# Otherwise mkdir throws an opaque error, or on Windows makes a reserved device path.
_RESERVED_NAMES = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
_UNSAFE_CHARS = set('<>:"/\\|?*') | {chr(c) for c in range(0, 32)}
_MAX_NAME_LEN = 200


def is_safe_name(name) -> bool:
    if not isinstance(name, str) or not name or name in (".", ".."):
        return False
    if len(name) > _MAX_NAME_LEN:
        return False
    if any(ch in _UNSAFE_CHARS for ch in name):
        return False
    if name != name.rstrip(". "):  # Windows strips trailing dot/space
        return False
    if name.split(".")[0].upper() in _RESERVED_NAMES:
        return False
    return True


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_run_meta(meta: dict, path: Path) -> None:
    """Write a run's meta atomically (temp file, then replace).

    getRuns and getRunStatus poll this file every few seconds while a run writes to
    it, so a half-written file would be read as corrupt. The worker already writes
    its own status file this way.
    """
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=True, indent=4)
    os.replace(tmp, path)


def _stable_hash(value) -> str:
    """A deterministic fingerprint for JSON-compatible execution inputs."""
    payload = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class OGCoreCase:
    def __init__(self, casename: str):
        self.casename = casename
        # Cases go in their own subfolder, not next to the registry/install entries.
        self.case_path = Path(Config.OGC_CASES_DIR, casename)
        self.gen_data_path = self.case_path / "genData.json"
        self.res_path = self.case_path / "res"
        self._gen_data: dict | None = None

    def run_params_path(self, run_name: str) -> Path:
        return self.res_path / run_name / "ogcParams.json"

    @property
    def gen_data(self) -> dict:
        if self._gen_data is None:
            self._gen_data = File.readFile(self.gen_data_path)
        return self._gen_data

    def _write_gen_data(self, data: dict) -> None:
        File.writeFile(data, self.gen_data_path)
        self._gen_data = None  # invalidate cache

    def create_case(self, gen_data: dict) -> dict:
        # exist_ok False on the case dir so a logic error fails loudly instead of
        # overwriting an existing case.
        if not is_safe_name(self.casename):
            return {"message": "Invalid case name.", "status_code": "error"}
        Config.OGC_CASES_DIR.mkdir(parents=True, exist_ok=True)
        self.case_path.mkdir(parents=True, exist_ok=False)
        self.res_path.mkdir(parents=True, exist_ok=True)
        gen_data["ogc-runs"] = []
        gen_data["ogc-version"] = "1.0"
        self._write_gen_data(gen_data)
        logger.info("Created OG-Core case '%s'", self.casename)
        return {"message": f"Case {self.casename} created.", "status_code": "created"}

    def save_case(self, gen_data: dict) -> dict:
        # Carry the run index and version forward so editing details never wipes runs.
        existing = self.gen_data
        gen_data["ogc-runs"] = existing.get("ogc-runs", [])
        gen_data["ogc-version"] = existing.get("ogc-version", "1.0")
        self._write_gen_data(gen_data)
        logger.info("Updated OG-Core case '%s'", self.casename)
        return {"message": f"Case {self.casename} updated.", "status_code": "edited"}

    def delete_case(self) -> dict:
        shutil.rmtree(self.case_path)
        logger.info("Deleted OG-Core case '%s'", self.casename)
        return {"message": f"Case {self.casename} deleted.", "status_code": "success_session"}

    @classmethod
    def list_cases(cls) -> list[dict]:
        # One bad case dir shouldn't break the whole listing, so log and skip it.
        cases: list[dict] = []
        cases_dir = Config.OGC_CASES_DIR
        if not cases_dir.is_dir():
            return cases
        for entry in sorted(cases_dir.iterdir()):
            if not entry.is_dir():
                continue
            gen_path = entry / "genData.json"
            try:
                gd = File.readFile(gen_path)
                mtime = gen_path.stat().st_mtime
            except (OSError, ValueError, KeyError) as exc:
                logger.warning("Skipping unreadable OG-Core case dir '%s': %s", entry.name, exc)
                continue
            modified_at = datetime.fromtimestamp(mtime, timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            cases.append({
                "casename": gd.get("ogc-casename", entry.name),
                "country_id": gd.get("country_id"),
                "description": gd.get("ogc-description", ""),
                "modified_at": modified_at,
                "has_results": cls._case_has_results(entry),
            })
        return cases

    @staticmethod
    def _case_has_results(case_dir: Path) -> bool:
        res_dir = case_dir / "res"
        if not res_dir.is_dir():
            return False
        try:
            run_dirs = [d for d in res_dir.iterdir() if d.is_dir()]
        except OSError:
            return False
        for run_dir in run_dirs:
            meta_path = run_dir / "run_meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = File.readFile(meta_path)
            except (OSError, ValueError, KeyError):
                continue
            if isinstance(meta, dict) and meta.get("status") == "completed":
                return True
        return False

    def get_params(self, run_name: str) -> dict:
        path = self.run_params_path(run_name)
        return File.readFile(path) if path.exists() else {}

    def save_params(self, run_name: str, params: dict) -> dict:
        run_dir = self.res_path / run_name
        if not run_dir.is_dir():
            return {"message": "Run not found.", "status_code": "error"}
        previous = self.get_params(run_name)
        File.writeFile(params, self.run_params_path(run_name))
        if previous != params:
            self.invalidate_run(
                run_name, "Parameters changed after the latest completed run."
            )
        return {"message": "Parameters saved.", "status_code": "success"}

    def create_run(
        self,
        run_name: str,
        run_type: str,
        baseline_run_name: str | None,
        params: dict | None = None,
    ) -> dict:
        # A reform must name an existing baseline; completion is checked later at
        # run time, not here.
        if not is_safe_name(run_name):
            return {"message": "Invalid run name.", "status_code": "error"}
        if not self.gen_data_path.exists():
            return {"message": "Case not found.", "status_code": "error"}
        if run_type not in ("baseline", "reform"):
            return {"message": "run_type must be 'baseline' or 'reform'.",
                    "status_code": "error"}

        run_path = self.res_path / run_name
        if run_path.exists():
            return {"message": "Run with same name already exists.", "status_code": "exist"}

        if run_type == "baseline":
            # One baseline per case; reforms read its outputs.
            if self.get_baseline_name() is not None:
                return {"message": "This case already has a baseline run.",
                        "status_code": "exist"}
            baseline_output_path = None
        else:  # reform
            if not baseline_run_name:
                return {"message": "baseline_run_name required for reform runs.",
                        "status_code": "error"}
            baseline_meta_path = self.res_path / baseline_run_name / "run_meta.json"
            if not baseline_meta_path.exists():
                return {"message": "Baseline run not found.", "status_code": "error"}
            index_entry = next(
                (r for r in self.gen_data.get("ogc-runs", [])
                 if r.get("RunName") == baseline_run_name),
                None,
            )
            if index_entry is None or index_entry.get("RunType") != "baseline":
                return {"message": "baseline_run_name must name a baseline run.",
                        "status_code": "error"}
            baseline_output_path = str(self.res_path / baseline_run_name)

        run_path.mkdir(parents=True, exist_ok=True)

        File.writeFile(params or {}, self.run_params_path(run_name))

        run_meta = {
            "run_name": run_name,
            "run_type": run_type,
            # The name is the portable half: the absolute path below is rewritten at
            # launch, so a case restored elsewhere still finds its baseline.
            "baseline_run_name": baseline_run_name if run_type == "reform" else None,
            "baseline_output_path": baseline_output_path,
            "time_path": None,
            "status": "pending",
            "error": None,
            "created_at": _utc_now_iso(),
            "completed_at": None,
            "attempt_id": None,
            "input_fingerprint": None,
            "result_fingerprint": None,
            "stale_reason": None,
        }
        _write_run_meta(run_meta, run_path / "run_meta.json")

        gd = self.gen_data
        runs = gd.get("ogc-runs", [])
        runs.append({
            "RunId": self._next_run_id(runs),
            "RunName": run_name,
            "RunType": run_type,
            "baseline_run_name": baseline_run_name,
        })
        gd["ogc-runs"] = runs
        self._write_gen_data(gd)
        logger.info("Created %s run '%s' in case '%s'", run_type, run_name, self.casename)
        return {"message": "Run created.", "status_code": "success"}

    @staticmethod
    def _next_run_id(runs: list) -> str:
        """Next unused run id. Counting entries would reuse an id after a delete."""
        highest = -1
        for run in runs:
            raw = str(run.get("RunId", ""))
            if raw.startswith("run_") and raw[4:].isdigit():
                highest = max(highest, int(raw[4:]))
        return f"run_{highest + 1}"

    def baseline_dir(self, run_name: str) -> Path | None:
        """Where this reform's baseline lives, resolved against this case.

        run_meta stores an absolute baseline path, which goes stale as soon as the
        case is restored on another machine or the install moves. Resolve from the
        baseline's name instead, falling back to the leaf of the stored path for
        runs created before the name was recorded.
        """
        meta = self.get_run_meta(run_name)
        if not meta:
            return None
        name = meta.get("baseline_run_name")
        if not name:
            stored = meta.get("baseline_output_path")
            name = Path(stored).name if stored else None
        if not name:
            return None
        return self.res_path / name

    def get_baseline_name(self) -> str | None:
        if not self.gen_data_path.exists():
            return None
        for run in self.gen_data.get("ogc-runs", []):
            if run.get("RunType") == "baseline":
                return run.get("RunName")
        return None

    def delete_run(self, run_name: str) -> dict:
        # Deleting the baseline removes the whole case, since every reform depends on it.
        if not self.gen_data_path.exists():
            return {"message": "Case not found.", "status_code": "error"}
        if self.get_baseline_name() == run_name:
            shutil.rmtree(self.case_path)
            logger.info("Deleted baseline run '%s'; removed case '%s'",
                        run_name, self.casename)
            return {
                "message": f"Baseline removed; case {self.casename} deleted.",
                "status_code": "success_session",
            }
        run_path = self.res_path / run_name
        if run_path.exists():
            shutil.rmtree(run_path)
        gd = self.gen_data
        gd["ogc-runs"] = [r for r in gd.get("ogc-runs", []) if r["RunName"] != run_name]
        self._write_gen_data(gd)
        logger.info("Deleted run '%s' from case '%s'", run_name, self.casename)
        return {"message": "Run deleted.", "status_code": "success"}

    def get_runs(self) -> list:
        # Run index with each run's live status from its run_meta. Entries are
        # copies so the status fields don't leak back into cached genData.
        if not self.gen_data_path.exists():
            return []
        enriched = []
        for run in self.gen_data.get("ogc-runs", []):
            item = dict(run)  # copy so we don't mutate cached gen_data
            meta_path = self.res_path / item["RunName"] / "run_meta.json"
            meta = None
            if meta_path.exists():
                # An unreadable meta must not break the whole listing; the run just
                # reads as pending until its next write.
                try:
                    meta = File.readFile(meta_path)
                except (OSError, ValueError, KeyError, IndexError):
                    meta = None
            if isinstance(meta, dict):
                item["status"] = meta.get("status", "pending")
                item["time_path"] = meta.get("time_path")
                item["completed_at"] = meta.get("completed_at")
                item["error"] = meta.get("error")
                item["reusable"] = self.is_run_reusable(item["RunName"])
                item["stale_reason"] = meta.get("stale_reason")
            else:
                item["status"] = "pending"
                item["time_path"] = None
                item["completed_at"] = None
                item["error"] = None
                item["reusable"] = False
                item["stale_reason"] = None
            enriched.append(item)
        return enriched

    def get_runs_shaped(self) -> dict:
        # Same as get_runs, split into the single baseline plus the list of reforms.
        baseline = None
        reforms = []
        for item in self.get_runs():
            if item.get("RunType") == "baseline":
                baseline = item
            else:
                reforms.append(item)
        return {"baseline": baseline, "reforms": reforms}

    def get_run_meta(self, run_name: str) -> dict:
        path = self.res_path / run_name / "run_meta.json"
        return File.readFile(path) if path.exists() else {}

    def update_run_status(
        self,
        run_name: str,
        status: str,
        error: str | None = None,
        time_path: bool | None = None,
    ) -> None:
        # Stamps completed_at when the run reaches a terminal state.
        path = self.res_path / run_name / "run_meta.json"
        meta = File.readFile(path)
        meta["status"] = status
        meta["error"] = error
        if time_path is not None:
            meta["time_path"] = time_path
        if status in ("completed", "failed"):
            meta["completed_at"] = _utc_now_iso()
            meta["pid"] = None  # the worker is gone; drop the stale pid
        if status == "completed":
            input_fingerprint = self.execution_input_fingerprint(
                run_name, meta.get("time_path")
            )
            meta["input_fingerprint"] = input_fingerprint
            meta["result_fingerprint"] = _stable_hash({
                "attempt_id": meta.get("attempt_id"),
                "input_fingerprint": input_fingerprint,
            })
            meta["stale_reason"] = None
        _write_run_meta(meta, path)

    def set_run_pid(self, run_name: str, pid) -> None:
        """Record the live worker's pid so a restart can clean up an orphan."""
        path = self.res_path / run_name / "run_meta.json"
        meta = File.readFile(path)
        meta["pid"] = pid
        _write_run_meta(meta, path)

    def stamp_execution(
        self,
        run_name: str,
        time_path: bool,
        country: dict,
        status: str,
    ) -> None:
        # Pin execution inputs when the FIFO accepts the run. Moving a persisted
        # queued run to running keeps the same attempt id.
        path = self.res_path / run_name / "run_meta.json"
        meta = File.readFile(path)
        was_queued = meta.get("status") == "queued"
        if not was_queued:
            meta["attempt_id"] = uuid.uuid4().hex
            meta["input_fingerprint"] = None
            meta["result_fingerprint"] = None
            meta["completed_at"] = None
            if meta.get("run_type") == "baseline":
                self.invalidate_dependents(
                    run_name, "The baseline was run again after this reform."
                )
        meta["time_path"] = time_path
        meta["country"] = country
        meta["status"] = status
        meta["error"] = None
        meta["stale_reason"] = None
        meta["pid"] = None  # set once the worker is actually spawned
        # Rewrite the baseline path from its name. The stored one is absolute, so it
        # is wrong for a case restored on another machine; the worker reads this file.
        name = meta.get("baseline_run_name")
        if not name and meta.get("baseline_output_path"):
            name = Path(meta["baseline_output_path"]).name
        if name:
            meta["baseline_run_name"] = name
            meta["baseline_output_path"] = str(self.res_path / name)
        _write_run_meta(meta, path)

    def set_run_provenance(self, run_name: str, provenance: dict) -> None:
        path = self.res_path / run_name / "run_meta.json"
        meta = File.readFile(path)
        meta["provenance"] = provenance
        _write_run_meta(meta, path)

    def _calibration_identity(self) -> dict:
        country_id = self.gen_data.get("country_id")
        record = CalibrationRegistry.get(country_id) or {}
        return {
            "country_id": country_id,
            "package_name": record.get("package_name"),
            "commit_sha": record.get("commit_sha"),
            "version": record.get("version"),
        }

    def execution_input_fingerprint(
        self, run_name: str, time_path: bool | None
    ) -> str:
        """Fingerprint every backend-owned input that makes results reusable."""
        meta = self.get_run_meta(run_name)
        tax_path = self.res_path / run_name / "ogcTaxParams.pkl"
        tax_hash = None
        if tax_path.exists():
            digest = hashlib.sha256()
            with open(tax_path, "rb") as tax_file:
                for chunk in iter(lambda: tax_file.read(1024 * 1024), b""):
                    digest.update(chunk)
            tax_hash = digest.hexdigest()
        baseline_result = None
        if meta.get("run_type") == "reform":
            baseline_dir = self.baseline_dir(run_name)
            baseline_meta = (
                File.readFile(baseline_dir / "run_meta.json")
                if baseline_dir and (baseline_dir / "run_meta.json").exists()
                else {}
            )
            baseline_result = baseline_meta.get("result_fingerprint")
        return _stable_hash({
            "params": self.get_params(run_name),
            "tax_params_sha256": tax_hash,
            "time_path": time_path,
            "calibration": self._calibration_identity(),
            "baseline_result_fingerprint": baseline_result,
        })

    def is_run_reusable(
        self, run_name: str, time_path: bool | None = None
    ) -> bool:
        """True only when completed metadata proves current execution inputs."""
        try:
            meta = self.get_run_meta(run_name)
        except (OSError, ValueError, KeyError, IndexError):
            return False
        if meta.get("status") != "completed" or not meta.get("input_fingerprint"):
            return False
        requested_time_path = meta.get("time_path") if time_path is None else time_path
        try:
            current = self.execution_input_fingerprint(run_name, requested_time_path)
        except (OSError, ValueError, KeyError, IndexError):
            return False
        return current == meta.get("input_fingerprint")

    def invalidate_run(self, run_name: str, reason: str) -> None:
        """Drop reusable-result authority for a run and its dependants."""
        path = self.res_path / run_name / "run_meta.json"
        if not path.exists():
            return
        meta = File.readFile(path)
        meta["status"] = "pending"
        meta["error"] = None
        meta["completed_at"] = None
        meta["pid"] = None
        meta["input_fingerprint"] = None
        meta["result_fingerprint"] = None
        meta["stale_reason"] = reason
        _write_run_meta(meta, path)
        if meta.get("run_type") == "baseline":
            self.invalidate_dependents(
                run_name, "The baseline changed after this reform was run."
            )

    def invalidate_dependents(self, baseline_run_name: str, reason: str) -> None:
        for run in self.gen_data.get("ogc-runs", []):
            if (
                run.get("RunType") == "reform"
                and run.get("baseline_run_name") == baseline_run_name
            ):
                path = self.res_path / run["RunName"] / "run_meta.json"
                if not path.exists():
                    continue
                meta = File.readFile(path)
                # A newly created reform is already pending and has no result to
                # invalidate; avoid replacing its neutral state with stale copy.
                if meta.get("result_fingerprint") is None and meta.get("status") == "pending":
                    continue
                meta["status"] = "pending"
                meta["error"] = None
                meta["completed_at"] = None
                meta["pid"] = None
                meta["input_fingerprint"] = None
                meta["result_fingerprint"] = None
                meta["stale_reason"] = reason
                _write_run_meta(meta, path)
