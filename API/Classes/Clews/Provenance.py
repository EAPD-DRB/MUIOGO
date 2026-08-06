"""The per-case provenance sidecar: where a case came from and how it was verified.

DataStorage is the source of truth for WHICH cases exist (a case is a directory
with a genData.json -- /getCases has always worked that way). What a bare directory
cannot say is where it came from: which repository, which archive, which checksum.
That is this sidecar's job: clews-provenance.json inside the case directory.

It rides inside the case deliberately. backupCase zips the whole case directory and
the importer restores everything, so provenance survives export -> hand-off ->
restore, and the receiving machine can still verify what it got.

All reads are tolerant: a missing or corrupt sidecar means "no provenance", never
an error -- plenty of perfectly good cases predate this file.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from Classes.Base import Config

SIDECAR_NAME = "clews-provenance.json"
SIDECAR_SCHEMA_VERSION = 1

# Chunked so hashing a large case archive does not hold it all in memory.
_HASH_CHUNK = 1024 * 1024


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_of(path):
    """Hex sha256 of a file, streamed."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(_HASH_CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


class Provenance:
    @staticmethod
    def sidecar_path(casename):
        return Path(Config.DATA_STORAGE, casename, SIDECAR_NAME)

    @classmethod
    def read(cls, casename):
        """The case's provenance record, or None (missing, corrupt, not a dict)."""
        path = cls.sidecar_path(casename)
        if not path.is_file():
            return None
        try:
            with open(path, mode="r", encoding="utf-8") as f:
                data = json.loads(f.read())
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    @classmethod
    def write(cls, casename, record):
        """Write the sidecar (stamping the schema version). Returns the record."""
        record = dict(record)
        record["schema_version"] = SIDECAR_SCHEMA_VERSION
        record["casename"] = casename
        path = cls.sidecar_path(casename)
        with open(path, mode="w", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=True, indent=4))
        return record

    @classmethod
    def build(cls, *, source, archive_path=None, archive_name=None,
              sha256_declared=None, case_version=None, extra=None):
        """Assemble a provenance record for a case being imported right now.

        ``source`` describes where the archive came from -- at minimum
        {"type": "upload" | "repo_url" | "catalog" | "local_path"}, plus whatever
        the source knows (repo_url, ref, commit_sha, vintage, iso3, country_name).
        ``archive_path`` (if the archive is still on disk) gets hashed; a declared
        checksum from a SHA256SUMS file is recorded next to the computed one, and
        ``verified`` says whether they matched.
        """
        record = {
            "source": dict(source),
            "installed_at": _now_iso(),
            "muio_version_at_install": _current_case_version(),
        }
        if case_version is not None:
            record["case_version"] = case_version
        archive = {}
        if archive_name:
            archive["name"] = archive_name
        if archive_path:
            archive["sha256_computed"] = sha256_of(archive_path)
        if sha256_declared:
            archive["sha256_declared"] = sha256_declared
            if archive.get("sha256_computed"):
                archive["verified"] = archive["sha256_computed"] == sha256_declared
        if archive:
            record["archive"] = archive
        if extra:
            record.update(extra)
        return record

    @classmethod
    def mark_copy(cls, src_casename, dst_casename):
        """Fix the sidecar inside a just-copied case, if it has one.

        A copytree'd sidecar would claim the copy IS the pristine installed archive.
        The copy keeps its lineage (derived_from) but loses the verified stamp --
        it is no longer the artifact the checksum was computed over. Best-effort:
        a copy without a sidecar is fine.
        """
        record = cls.read(dst_casename)
        if record is None:
            return None
        record["derived_from"] = src_casename
        record["copied_at"] = _now_iso()
        archive = record.get("archive")
        if isinstance(archive, dict):
            archive.pop("verified", None)
        return cls.write(dst_casename, record)


def _current_case_version():
    # Imported lazily to keep this module import-light (CaseImporter imports us).
    from Classes.Case.CaseImporter import CURRENT_CASE_VERSION
    return CURRENT_CASE_VERSION
