"""CaseImporter.import_zip: the shared import pipeline behind /uploadCase and installers.

These pin the behavior the refactor moved out of UploadRoute.handle_full_zip:
message shapes, the version ladder, duplicate refusal, legacy arcnames, cleanup.
"""
import pytest

from Classes.Base import Config
from Classes.Case.CaseImporter import (
    ACCEPTED_CASE_VERSIONS,
    CURRENT_CASE_VERSION,
    CaseImporter,
)

from .conftest import make_case_zip, minimal_gendata


def test_import_current_version_succeeds(clews_storage, tmp_path):
    zip_path = make_case_zip(tmp_path, "TestCase56", version="5.6")
    msg = CaseImporter.import_zip(str(zip_path))
    assert msg == [{
        "message": "Model TestCase56 have been uploaded!",
        "status_code": "success",
        "casename": "TestCase56",
    }]
    case_dir = clews_storage / "TestCase56"
    assert (case_dir / "genData.json").is_file()
    # The 5.6 rung rebuilds view definitions from Variables.json + Indicators.json.
    assert (case_dir / "view" / "viewDefinitions.json").is_file()


@pytest.mark.parametrize("version", ACCEPTED_CASE_VERSIONS)
def test_every_accepted_version_has_a_ladder_rung(clews_storage, tmp_path, version):
    """ACCEPTED_CASE_VERSIONS is what /getVersion advertises; each member must
    actually import (guards the constant against drifting from the ladder)."""
    casename = f"Case_{version.replace('.', '_')}"
    zip_path = make_case_zip(tmp_path, casename, version=version)
    msg = CaseImporter.import_zip(str(zip_path))
    assert msg[0]["status_code"] in ("success", "warning")
    assert msg[0].get("casename") == casename
    assert (clews_storage / casename / "genData.json").is_file()


def test_unknown_version_is_refused(clews_storage, tmp_path):
    zip_path = make_case_zip(tmp_path, "FutureCase", version="99.0")
    msg = CaseImporter.import_zip(str(zip_path))
    assert msg[0]["status_code"] == "error"
    assert "not valid OSEMOSYS" in msg[0]["message"]
    assert not (clews_storage / "FutureCase" / "view" / "viewDefinitions.json").exists()


def test_zip_without_gendata_is_invalid_archive(clews_storage, tmp_path):
    import zipfile
    zip_path = tmp_path / "junk.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("whatever/readme.txt", "not a case")
    msg = CaseImporter.import_zip(str(zip_path))
    assert msg == [{
        "message": "ZIP archive junk is not valid archive!",
        "status_code": "error",
    }]
    # The historical early-return path never removed the archive.
    assert zip_path.exists()


def test_existing_case_is_not_overwritten(clews_storage, tmp_path):
    (clews_storage / "TestCase56").mkdir()
    marker = clews_storage / "TestCase56" / "keep.txt"
    marker.write_text("original")
    zip_path = make_case_zip(tmp_path, "TestCase56", version="5.6")
    msg = CaseImporter.import_zip(str(zip_path))
    assert msg[0]["status_code"] == "warning"
    assert "already exists" in msg[0]["message"]
    assert marker.read_text() == "original"
    assert not zip_path.exists()  # this path has always cleaned up the archive


def test_cleanup_false_keeps_the_archive(clews_storage, tmp_path):
    zip_path = make_case_zip(tmp_path, "KeepZip", version="5.6")
    CaseImporter.import_zip(str(zip_path), cleanup=False)
    assert zip_path.exists()
    assert (clews_storage / "KeepZip" / "genData.json").is_file()


def test_legacy_arcname_prefix_still_imports(clews_storage, tmp_path):
    """Backups made before PR #331 root entries at WebAPP/DataStorage/<case>/."""
    zip_path = make_case_zip(tmp_path, "LegacyCase", version="5.6",
                             arc_prefix="WebAPP/DataStorage/")
    msg = CaseImporter.import_zip(str(zip_path))
    assert msg[0]["status_code"] == "success"
    assert (clews_storage / "LegacyCase" / "genData.json").is_file()


def test_current_version_is_accepted():
    assert CURRENT_CASE_VERSION in ACCEPTED_CASE_VERSIONS
