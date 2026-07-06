"""Persistent registry of OG calibrations this machine has installed/registered.

This is the only OG list MUIOGO owns. The available-country catalogue is reflected
live from the installer's register (see CalibrationCatalog); here we keep just what
the user has actually installed or pointed at, plus its env paths so the run layer
can launch against the right interpreter.

Stored at Config.OGC_INSTALLED_REGISTRY as:

    { "calibrations": { "<country_id>": { ...record... } } }

A record carries: country_id, country_name, source_type (catalog|repo_url|local_path),
local_path, venv_path, python_path, package_name, repo_url, commit_sha, install_state,
installed_at, last_checked_at.
"""
import json
import os
import tempfile
import threading

from Classes.Base import Config

# Writes happen from request threads and from background install threads, so guard
# the read-modify-write with a process-wide lock.
_LOCK = threading.RLock()


class CalibrationRegistry:
    @staticmethod
    def _ensure_dir():
        Config.OGC_DATA_STORAGE.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _load():
        """Return the registry dict, tolerating a missing or corrupt file."""
        path = Config.OGC_INSTALLED_REGISTRY
        if not path.exists():
            return {"calibrations": {}}
        try:
            with open(path, mode="r", encoding="utf-8") as f:
                data = json.loads(f.read())
        except (OSError, ValueError):
            # A corrupt registry should not take the whole API down. Treat as empty;
            # the next successful save rewrites it cleanly.
            return {"calibrations": {}}
        if not isinstance(data, dict) or not isinstance(data.get("calibrations"), dict):
            return {"calibrations": {}}
        return data

    @staticmethod
    def _save(data):
        """Atomic write: temp file in the same dir, then os.replace."""
        CalibrationRegistry._ensure_dir()
        path = Config.OGC_INSTALLED_REGISTRY
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, mode="w", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=True, indent=4, sort_keys=False))
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    @classmethod
    def list_all(cls):
        """All installed/registered calibration records, as a list."""
        with _LOCK:
            data = cls._load()
        return list(data["calibrations"].values())

    @classmethod
    def get(cls, country_id):
        """One record by country_id, or None."""
        if not country_id:
            return None
        with _LOCK:
            data = cls._load()
        return data["calibrations"].get(country_id)

    @classmethod
    def upsert(cls, record):
        """Insert or replace the record for record['country_id']."""
        country_id = record.get("country_id")
        if not country_id:
            raise ValueError("calibration record requires a country_id")
        with _LOCK:
            data = cls._load()
            data["calibrations"][country_id] = record
            cls._save(data)
        return record

    @classmethod
    def update_fields(cls, country_id, **fields):
        """Patch named fields on an existing record. Returns the record or None."""
        with _LOCK:
            data = cls._load()
            record = data["calibrations"].get(country_id)
            if record is None:
                return None
            record.update(fields)
            cls._save(data)
        return record

    @classmethod
    def remove(cls, country_id):
        """Drop the registry entry. Returns the removed record, or None."""
        with _LOCK:
            data = cls._load()
            record = data["calibrations"].pop(country_id, None)
            if record is not None:
                cls._save(data)
        return record

    @classmethod
    def exists(cls, country_id):
        return cls.get(country_id) is not None
