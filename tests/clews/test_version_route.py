"""/getVersion and the /uploadCase route after the CaseImporter extraction.

The route tests drive the real HTTP path end to end, through both the unchunked
branch and the chunked Dropzone branch the browser uses, proving the refactor
preserved what the browser upload does.
"""
import io

from Classes.Case.CaseImporter import ACCEPTED_CASE_VERSIONS, CURRENT_CASE_VERSION

from .conftest import make_case_zip


def test_get_version_reports_current_and_accepted(client):
    resp = client.get("/getVersion")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["muio_version"] == CURRENT_CASE_VERSION
    assert body["accepted_case_versions"] == list(ACCEPTED_CASE_VERSIONS)


def test_get_version_wrong_method_returns_405(client):
    resp = client.post("/getVersion")
    assert resp.status_code == 405


def test_upload_case_route_still_imports(client, clews_storage, tmp_path):
    """POST a case zip through /uploadCase (no dzuuid -> the unchunked branch)."""
    zip_path = make_case_zip(tmp_path, "RouteCase", version="5.6")
    data = {"file": (io.BytesIO(zip_path.read_bytes()), "RouteCase.zip")}
    resp = client.post("/uploadCase", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["response"][0]["status_code"] == "success"
    assert body["response"][0]["casename"] == "RouteCase"
    assert (clews_storage / "RouteCase" / "genData.json").is_file()
    # The upload flow removes the saved archive from DataStorage after import.
    assert not (clews_storage / "RouteCase.zip").exists()


def test_upload_case_route_rejects_duplicate(client, clews_storage, tmp_path):
    (clews_storage / "DupCase").mkdir()
    zip_path = make_case_zip(tmp_path, "DupCase", version="5.6")
    data = {"file": (io.BytesIO(zip_path.read_bytes()), "DupCase.zip")}
    resp = client.post("/uploadCase", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert resp.get_json()["response"][0]["status_code"] == "warning"


def test_upload_case_route_imports_chunked_upload(client, clews_storage, tmp_path):
    """POST a case zip in two Dropzone chunks (dzuuid set -> the chunked branch).

    This is how the browser restores a backup. The merged archive must reach the
    importer rather than be refused as an invalid path.
    """
    zip_bytes = make_case_zip(tmp_path, "ChunkCase", version="5.6").read_bytes()
    half = len(zip_bytes) // 2
    dz_uuid = "3f2b8c1e-0000-4000-8000-000000000557"
    for index, part in enumerate((zip_bytes[:half], zip_bytes[half:])):
        data = {
            "dzuuid": dz_uuid,
            "dzchunkindex": str(index),
            "dztotalchunkcount": "2",
            "file": (io.BytesIO(part), "ChunkCase.zip"),
        }
        resp = client.post("/uploadCase", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["response"][0]["status_code"] == "success"
    assert body["response"][0]["casename"] == "ChunkCase"
    assert (clews_storage / "ChunkCase" / "genData.json").is_file()
    # Both the merged archive and the chunk folder are removed after import.
    assert not (clews_storage / f"{dz_uuid}.zip").exists()
    assert not (clews_storage / "_chunks").exists()
