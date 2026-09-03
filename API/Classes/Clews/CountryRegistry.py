"""Persistent index of the CLEWs cases on this machine, reconciled against DataStorage.

DataStorage itself is the source of truth for WHICH cases exist -- this index never
overrides a directory listing. What it adds is durable bookkeeping per case (where
it came from, when it was installed, its install state) plus one honest extra
state: ``unmanaged``, a case that is on disk but was never installed through a
tracked path (dropped in by hand, or predates this layer).

Because users add and remove case directories by hand, the index is treated as a
cache and *reconciled* against a DataStorage scan: on server launch and on every
installed-list read. A case is a directory holding a genData.json; anything else
in DataStorage (param files, upload staging) is ignored.

The index describes ONE DataStorage, so it lives inside it (the dot-file
Config.CLEWS_REGISTRY_BASENAME at the storage root, next to Parameters.json and
friends) rather than at the user level -- several MUIOGO checkouts on one machine
each keep their own. Stored as:

    { "cases": { "<casename>": { ...record... } } }
"""
import json
import logging
import os
import tempfile
import threading
from pathlib import Path

from Classes.Base import Config
from Classes.Base.FileClass import File
from Classes.Clews.Provenance import Provenance

# Writes happen from request threads and from background install threads, so guard
# the read-modify-write with a process-wide lock (same pattern as CalibrationRegistry).
_LOCK = threading.RLock()

# Sidecar fields the index carries per managed case. The sidecar stays the full
# record; the index holds what lists and update checks need.
_INDEXED_SIDECAR_FIELDS = (
    "iso3", "un_code", "country_name", "source", "archive", "vintage", "role",
    "case_version", "installed_at", "derived_from",
)


def _registry_path():
    """Resolved at call time so it always tracks the active DATA_STORAGE."""
    return Path(Config.DATA_STORAGE, Config.CLEWS_REGISTRY_BASENAME)


class CountryRegistry:
    @staticmethod
    def _load():
        """Return the registry dict, tolerating a missing or corrupt file."""
        path = _registry_path()
        if not path.exists():
            return {"cases": {}}
        try:
            with open(path, mode="r", encoding="utf-8") as f:
                data = json.loads(f.read())
        except (OSError, ValueError):
            return {"cases": {}}
        if not isinstance(data, dict) or not isinstance(data.get("cases"), dict):
            return {"cases": {}}
        return data

    @staticmethod
    def _save(data):
        """Atomic write: temp file in the same dir, then os.replace."""
        path = _registry_path()
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

    # ── plain record access ──────────────────────────────────────────────────
    @classmethod
    def list_all(cls):
        with _LOCK:
            data = cls._load()
        return list(data["cases"].values())

    @classmethod
    def get(cls, casename):
        if not casename:
            return None
        with _LOCK:
            data = cls._load()
        return data["cases"].get(casename)

    @classmethod
    def upsert(cls, record):
        casename = record.get("casename")
        if not casename:
            raise ValueError("case record requires a casename")
        with _LOCK:
            data = cls._load()
            data["cases"][casename] = record
            cls._save(data)
        return record

    @classmethod
    def remove(cls, casename):
        with _LOCK:
            data = cls._load()
            record = data["cases"].pop(casename, None)
            if record is not None:
                cls._save(data)
        return record

    # ── reconcile against DataStorage ────────────────────────────────────────
    @staticmethod
    def _scan_case_dirs():
        """Casenames actually on disk: directories holding a genData.json."""
        try:
            entries = os.scandir(Config.DATA_STORAGE)
        except OSError:
            return set()
        found = set()
        for entry in entries:
            try:
                if entry.is_dir() and os.path.isfile(os.path.join(entry.path, "genData.json")):
                    found.add(entry.name)
            except OSError:
                continue
        return found

    @staticmethod
    def _case_version(casename):
        """The case's own osy-version, or None. Cheap enough to refresh per scan."""
        try:
            genData = File.readFile(os.path.join(Config.DATA_STORAGE, casename, "genData.json"))
            return genData.get("osy-version")
        except (OSError, ValueError, IndexError, AttributeError):
            return None

    @classmethod
    def _record_from_sidecar(cls, casename, sidecar):
        record = {
            "casename": casename,
            "managed": True,
            "install_state": "installed",
        }
        source = sidecar.get("source")
        if isinstance(source, dict):
            record["source_type"] = source.get("type")
        for field in _INDEXED_SIDECAR_FIELDS:
            if sidecar.get(field) is not None:
                record[field] = sidecar[field]
        # Country identity is recorded inside the sidecar's source block; lift it
        # to the top of the record so list consumers get cases[].iso3 directly.
        if isinstance(source, dict):
            for field in ("iso3", "un_code", "country_name", "vintage", "role"):
                if record.get(field) is None and source.get(field) is not None:
                    record[field] = source[field]
        return record

    @classmethod
    def reconcile(cls):
        """Bring the index in line with what is actually in DataStorage.

        - a case on disk with a provenance sidecar -> (re)indexed from the sidecar
        - a case on disk without one -> recorded as unmanaged (added by hand,
          or predates this layer); its first_seen_at is preserved across runs
        - an index entry whose directory is gone -> dropped (removed by hand)

        Returns {"adopted": [...], "unmanaged": [...], "removed": [...],
        "total": n} describing what changed / what is untracked. Idempotent: a
        second run over an unchanged DataStorage reports no adoptions or removals.
        """
        on_disk = cls._scan_case_dirs()
        adopted, unmanaged = [], []
        with _LOCK:
            data = cls._load()
            cases = data["cases"]

            removed = sorted(name for name in cases if name not in on_disk)
            for name in removed:
                cases.pop(name)

            for name in sorted(on_disk):
                existing = cases.get(name)
                sidecar = Provenance.read(name)
                if sidecar is not None:
                    record = cls._record_from_sidecar(name, sidecar)
                    record["case_version"] = cls._case_version(name)
                    if existing is None or not existing.get("managed"):
                        adopted.append(name)
                    # Keep runtime fields a plain re-index must not erase.
                    if existing:
                        for keep in ("install_id", "last_checked_at", "update_available"):
                            if keep in existing:
                                record.setdefault(keep, existing[keep])
                    cases[name] = record
                else:
                    if existing is None:
                        unmanaged.append(name)
                        cases[name] = {
                            "casename": name,
                            "managed": False,
                            "source_type": "unmanaged",
                            "install_state": "unmanaged",
                            "first_seen_at": _now_iso(),
                            "case_version": cls._case_version(name),
                        }
                    else:
                        existing["case_version"] = cls._case_version(name)

            cls._save(data)
            total = len(cases)

        return {"adopted": adopted, "unmanaged": unmanaged, "removed": removed,
                "total": total}

    @classmethod
    def reconcile_safe(cls):
        """reconcile() for server startup: never raises, logs one summary line."""
        log = logging.getLogger(__name__)
        try:
            summary = cls.reconcile()
        except Exception as exc:  # startup housekeeping must never crash the app
            log.warning("CLEWs case reconcile skipped: %s", exc)
            return None
        parts = [f"{summary['total']} case(s) indexed"]
        if summary["adopted"]:
            parts.append(f"adopted {len(summary['adopted'])}: {', '.join(summary['adopted'])}")
        if summary["unmanaged"]:
            parts.append(f"untracked {len(summary['unmanaged'])}: {', '.join(summary['unmanaged'])}")
        if summary["removed"]:
            parts.append(f"dropped {len(summary['removed'])} removed from disk: {', '.join(summary['removed'])}")
        log.info("CLEWs case registry: %s.", "; ".join(parts))
        return summary


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
