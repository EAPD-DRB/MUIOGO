"""Shared setup for the CLEWs case-import/install tests.

Points Config.DATA_STORAGE at a per-test temp dir (seeded with the real
Variables.json / Indicators.json, which the view-definitions migration reads), so
imports never touch the repo's own DataStorage. Autouse, but scoped to this package
only -- the rest of the suite still runs against the checked-in DataStorage.
"""
import json
import shutil
import zipfile
from pathlib import Path

import pytest

from Classes.Base import Config

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
