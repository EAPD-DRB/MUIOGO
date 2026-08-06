"""The clews-provenance.json sidecar: build, roundtrip, checksum, copy restamp."""
import json

from Classes.Case.CaseImporter import CURRENT_CASE_VERSION, CaseImporter
from Classes.Clews.Provenance import Provenance, sha256_of

from .conftest import make_case_zip


def test_build_hashes_and_verifies_against_declared(tmp_path):
    payload = tmp_path / "case.zip"
    payload.write_bytes(b"archive bytes")
    good = sha256_of(payload)

    record = Provenance.build(
        source={"type": "repo_url", "repo_url": "https://example.org/x"},
        archive_path=str(payload), archive_name="case.zip", sha256_declared=good,
    )
    assert record["archive"]["verified"] is True
    assert record["archive"]["sha256_computed"] == good
    assert record["muio_version_at_install"] == CURRENT_CASE_VERSION

    bad = Provenance.build(source={"type": "repo_url"}, archive_path=str(payload),
                           sha256_declared="0" * 64)
    assert bad["archive"]["verified"] is False


def test_write_read_roundtrip(clews_storage):
    (clews_storage / "SomeCase").mkdir()
    Provenance.write("SomeCase", {"source": {"type": "upload"}})
    back = Provenance.read("SomeCase")
    assert back["casename"] == "SomeCase"
    assert back["schema_version"] == 1
    assert back["source"] == {"type": "upload"}


def test_read_tolerates_missing_and_corrupt(clews_storage):
    assert Provenance.read("NoSuchCase") is None
    (clews_storage / "BadCase").mkdir()
    Provenance.sidecar_path("BadCase").write_text("{ not json")
    assert Provenance.read("BadCase") is None


def test_import_zip_writes_sidecar(clews_storage, tmp_path):
    zip_path = make_case_zip(tmp_path, "WithProv", version="5.6")
    declared = sha256_of(zip_path)
    CaseImporter.import_zip(str(zip_path), cleanup=False,
                            source={"type": "repo_url", "iso3": "PHL"},
                            sha256_declared=declared)
    sidecar = Provenance.read("WithProv")
    assert sidecar["source"]["iso3"] == "PHL"
    assert sidecar["archive"]["verified"] is True
    assert sidecar["case_version"] == "5.6"


def test_import_zip_default_source_is_upload(clews_storage, tmp_path):
    zip_path = make_case_zip(tmp_path, "PlainUpload", version="5.6")
    CaseImporter.import_zip(str(zip_path))
    sidecar = Provenance.read("PlainUpload")
    assert sidecar["source"] == {"type": "upload"}
    assert "sha256_computed" in sidecar["archive"]


def test_refused_duplicate_gets_no_sidecar(clews_storage, tmp_path):
    (clews_storage / "Dup").mkdir()
    zip_path = make_case_zip(tmp_path, "Dup", version="5.6")
    CaseImporter.import_zip(str(zip_path))
    assert Provenance.read("Dup") is None


def test_mark_copy_restamps_lineage(clews_storage):
    (clews_storage / "Orig").mkdir()
    Provenance.write("Orig", {
        "source": {"type": "repo_url"},
        "archive": {"name": "a.zip", "sha256_computed": "x", "verified": True},
    })
    (clews_storage / "Orig_copy").mkdir()
    src = Provenance.sidecar_path("Orig").read_text()
    Provenance.sidecar_path("Orig_copy").write_text(src)  # what copytree does

    Provenance.mark_copy("Orig", "Orig_copy")
    copy = Provenance.read("Orig_copy")
    assert copy["derived_from"] == "Orig"
    assert copy["casename"] == "Orig_copy"
    assert "verified" not in copy["archive"]
    # The original is untouched.
    assert Provenance.read("Orig")["archive"]["verified"] is True


def test_copy_case_route_restamps_sidecar(client, clews_storage, tmp_path):
    zip_path = make_case_zip(tmp_path, "RouteOrig", version="5.6")
    CaseImporter.import_zip(str(zip_path))
    resp = client.post("/setSession", json={"case": "RouteOrig"})
    assert resp.status_code == 200
    resp = client.post("/copyCase", json={"casename": "RouteOrig"})
    assert resp.status_code == 200
    assert "copied" in resp.get_json()["message"]

    copy = Provenance.read("RouteOrig_copy")
    assert copy["derived_from"] == "RouteOrig"
    # genData in the copy was renamed too (pre-existing behavior, still true).
    gen = json.loads((clews_storage / "RouteOrig_copy" / "genData.json").read_text())
    assert gen["osy-casename"] == "RouteOrig_copy"
