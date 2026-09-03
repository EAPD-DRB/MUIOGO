"""Shared setup for the CLEWs case-import/install tests.

Points Config.DATA_STORAGE at a per-test temp dir (seeded with the real
Variables.json / Indicators.json, which the view-definitions migration reads), so
imports never touch the repo's own DataStorage. Autouse, but scoped to this package
only -- the rest of the suite still runs against the checked-in DataStorage.
"""
import json
import shutil
import time
import zipfile
from pathlib import Path

import pytest

from Classes.Base import Config
from Classes.Clews.ClewsInstallJob import ClewsInstallJob
from Classes.Clews.Provenance import sha256_of

# The repo's real DataStorage: the source for the param files every import needs.
_REAL_STORAGE = Path(Config.DATA_STORAGE)


@pytest.fixture(autouse=True)
def clews_storage(tmp_path, monkeypatch):
    """An isolated DataStorage carrying the app-level param files."""
    storage = tmp_path / "DataStorage"
    storage.mkdir()
    for name in ("Variables.json", "Indicators.json", "Parameters.json", "Duals.json"):
        src = _REAL_STORAGE / name
        if src.exists():
            shutil.copy(src, storage / name)
    monkeypatch.setattr(Config, "DATA_STORAGE", storage)
    yield storage


@pytest.fixture(autouse=True)
def clews_state(tmp_path, monkeypatch):
    """Isolated CLEWs machine-level state (install jobs, download staging).

    The installed-case registry needs no patching here: it lives inside
    DataStorage itself, which clews_storage already isolates.
    """
    state = tmp_path / "clews-state"
    monkeypatch.setattr(Config, "CLEWS_DATA_STORAGE", state)
    monkeypatch.setattr(Config, "CLEWS_INSTALL_JOBS_DIR", state / "install_jobs")
    monkeypatch.setattr(Config, "CLEWS_DOWNLOADS_DIR", state / "downloads")
    monkeypatch.setattr(Config, "CLEWS_CATALOG_CACHE", state / "catalog_cache.json")
    yield state


def _drain_jobs(timeout=6.0):
    """Wait for any launched worker before clearing state, so a failing test's
    thread cannot wake later and write into the next test's patched paths."""
    deadline = time.monotonic() + timeout
    while ClewsInstallJob.active_count() and time.monotonic() < deadline:
        time.sleep(0.05)


@pytest.fixture(autouse=True)
def clews_jobs():
    """Reset ClewsInstallJob's in-memory class state around every test."""
    yield
    _drain_jobs()
    with ClewsInstallJob._lock:
        ClewsInstallJob._jobs.clear()
        ClewsInstallJob._active_by_key.clear()
        ClewsInstallJob._cancel_by_id.clear()
        ClewsInstallJob._shutting_down = False


def wait_for_job(install_id, timeout=10.0):
    """Poll a job to a terminal state; fail loudly on timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = ClewsInstallJob.get_status(install_id)
        if job and job["install_state"] in ("installed", "failed"):
            return job
        time.sleep(0.02)
    raise AssertionError(f"install {install_id} did not finish within {timeout}s")


def build_country_repo(root, iso3="TST", name="Testland"):
    """A complete fixture country repo on disk: manifest, two vintages, checksums.

    v1 (old) ships OldCase; v2 (recommended) ships CaseA (recommended) + CaseB.
    Archives are real importable 5.6 case zips. Returns the repo path.
    """
    repo = Path(root) / "country-repo"
    v1 = repo / "build_v1" / "muio"
    v2 = repo / "build_v2" / "muio"
    v1.mkdir(parents=True)
    v2.mkdir(parents=True)

    z_old = make_case_zip(v1, "OldCase", version="5.6")
    z_a = make_case_zip(v2, "CaseA", version="5.6")
    z_b = make_case_zip(v2, "CaseB", version="5.6")
    (v1 / "SHA256SUMS").write_text(f"{sha256_of(z_old)}  OldCase.zip\n")
    (v2 / "SHA256SUMS").write_text(
        f"{sha256_of(z_a)}  CaseA.zip\n{sha256_of(z_b)}  CaseB.zip\n")

    manifest = {
        "schema_version": 1,
        "iso3": iso3,
        "un_code": "999",
        "name": name,
        "og": {"key": f"og-{iso3.lower()}"},
        "vintages": [
            {"id": "v1", "dir": "build_v1/muio", "sha256sums": "SHA256SUMS",
             "cases": [{"case": "OldCase", "archive": "OldCase.zip"}]},
            {"id": "v2", "recommended": True, "dir": "build_v2/muio",
             "sha256sums": "SHA256SUMS", "muio_min_version": "5.6",
             "cases": [
                 {"case": "CaseA", "role": "analysis", "recommended": True,
                  "archive": "CaseA.zip"},
                 {"case": "CaseB", "role": "source", "archive": "CaseB.zip"},
             ]},
        ],
    }
    (repo / "clews-country.json").write_text(json.dumps(manifest, indent=2))
    return repo


def minimal_gendata(casename, version):
    """The smallest genData.json every migration rung can digest.

    osy-ns / osy-dt feed updateTimeslices (int()'d) on the pre-5.0 rungs; osy-tech
    and osy-indicators feed the view-definitions rebuild on every rung.
    """
    return {
        "osy-casename": casename,
        "osy-version": version,
        "osy-desc": "test case",
        "osy-ns": 1,
        "osy-dt": 1,
        "osy-tech": [],
        "osy-indicators": [],
    }


def make_case_zip(dest_dir, casename, version="5.6", arc_prefix="", gendata=None):
    """Build a fixture case archive like backupCase produces.

    arc_prefix="WebAPP/DataStorage/" reproduces the pre-#331 legacy layout.
    Returns the path to the written zip.
    """
    gendata = gendata if gendata is not None else minimal_gendata(casename, version)
    zip_path = Path(dest_dir) / f"{casename}.zip"
    entries = {
        f"{casename}/genData.json": json.dumps(gendata),
        # The timeslice rename step rewrites these on the pre-5.0 rungs.
        f"{casename}/RYTs.json": "{}",
        f"{casename}/RYTTs.json": "{}",
        f"{casename}/RYCTs.json": "{}",
        # view/ must ship in the archive: the 3.0+ rungs write viewDefinitions.json
        # into it without creating the directory.
        f"{casename}/view/viewDefinitions.json": json.dumps({"osy-views": {}}),
        f"{casename}/view/resData.json": json.dumps({"osy-cases": []}),
    }
    with zipfile.ZipFile(zip_path, "w") as zf:
        for arcname, payload in entries.items():
            zf.writestr(arc_prefix + arcname, payload)
    return zip_path
