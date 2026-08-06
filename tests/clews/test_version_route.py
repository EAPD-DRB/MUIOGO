"""/getVersion and the /uploadCase route after the CaseImporter extraction.

The route test drives the real HTTP path (unchunked branch) end to end, proving
the refactor preserved what the browser upload does.
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
