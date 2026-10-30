"""Case backups must not write into another case or shared configuration."""
import io
import json
import stat
from zipfile import ZipFile, ZipInfo

import pytest

from Classes.Case.CaseImporter import CaseImporter

from .conftest import make_case_zip


def _archive(tmp_path, entries):
    path = tmp_path / "upload.zip"
    with ZipFile(path, "w") as zf:
        for name, content in entries:
            zf.writestr(name, content)
    return path


def _post_archive(client, payload, transport, filename="backup.zip"):
    data = {"file": (io.BytesIO(payload), filename)}
    route = "/uploadCase"
    if transport == "chunked":
        data.update(dzuuid="security-review", dzchunkindex="0", dztotalchunkcount="1")
    elif transport == "legacy":
        route = "/uploadCaseUnchunked_old"
    return client.post(route, data=data, content_type="multipart/form-data")


@pytest.mark.parametrize("prefix", ["", "WebAPP/DataStorage/"])
@pytest.mark.parametrize("bad_entry", [
    "Existing/RYC.json", "Variables.json", "Parameters.json", "NewCaseExtra/file.txt",
    "NewCase/../Existing/RYC.json", "../outside.txt", "/absolute.txt",
    "C:/outside.txt", "NewCase/../../outside.txt", "NewCase\\..\\outside.txt",
    "NewCase/nested:stream", "NewCase//file.txt", "OtherCase/",
])
def test_rejects_out_of_case_entries_before_writing(clews_storage, tmp_path, prefix, bad_entry):
    existing = clews_storage / "Existing"
    existing.mkdir()
    (existing / "RYC.json").write_text("original demand")
    before = {p.relative_to(clews_storage): p.read_bytes()
              for p in clews_storage.rglob("*") if p.is_file()}
    path = _archive(tmp_path, [
        (prefix + "NewCase/genData.json", json.dumps({"osy-version": "5.7"})),
        (prefix + "NewCase/valid.txt", "must not be partially extracted"),
        (bad_entry, "attacker content"),
    ])
    with pytest.raises(PermissionError):
        CaseImporter.import_zip(str(path))
    assert not (clews_storage / "NewCase").exists()
    after = {p.relative_to(clews_storage): p.read_bytes()
             for p in clews_storage.rglob("*") if p.is_file()}
    assert after == before


@pytest.mark.parametrize("metadata", [
    "genData.json", "nested/NewCase/genData.json", "../NewCase/genData.json",
    "/NewCase/genData.json", "C:/NewCase/genData.json", "NewCase\\genData.json",
])
def test_rejects_ambiguous_or_unsafe_case_roots(clews_storage, tmp_path, metadata):
    path = _archive(tmp_path, [(metadata, '{"osy-version": "5.7"}')])
    with pytest.raises(PermissionError):
        CaseImporter.import_zip(str(path))
    assert not (clews_storage / "NewCase").exists()


def test_rejects_multiple_metadata_entries(clews_storage, tmp_path):
    path = _archive(tmp_path, [
        ("First/genData.json", '{"osy-version": "5.7"}'),
        ("Second/genData.json", '{"osy-version": "5.7"}'),
    ])
    with pytest.raises(PermissionError):
        CaseImporter.import_zip(str(path))
    assert not (clews_storage / "First").exists()
    assert not (clews_storage / "Second").exists()


def test_rejects_duplicate_normalized_members(clews_storage, tmp_path):
    path = _archive(tmp_path, [
        ("NewCase/genData.json", '{"osy-version": "5.7"}'),
        ("NewCase/value.json", "first value"),
        ("WebAPP/DataStorage/NewCase/value.json", "replacement value"),
    ])
    with pytest.raises(PermissionError):
        CaseImporter.import_zip(str(path))
    assert not (clews_storage / "NewCase").exists()


def test_rejects_symlink_entries_before_writing(clews_storage, tmp_path):
    link = ZipInfo("NewCase/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    path = _archive(tmp_path, [
        ("NewCase/genData.json", '{"osy-version": "5.7"}'),
        (link, str(tmp_path / "outside")),
    ])
    with pytest.raises(PermissionError):
        CaseImporter.import_zip(str(path))
    assert not (clews_storage / "NewCase").exists()


def test_rejects_nul_truncated_zip_names(clews_storage, tmp_path):
    path = _archive(tmp_path, [
        ("NewCase/genData.json", '{"osy-version": "5.7"}'),
        ("NewCase/valueXfile.txt", "untrusted content"),
    ])
    # Patch both ZIP headers because ZipInfo's writer itself truncates NUL names.
    path.write_bytes(path.read_bytes().replace(b"valueXfile", b"value\x00file"))
    with pytest.raises(PermissionError):
        CaseImporter.import_zip(str(path))
    assert not (clews_storage / "NewCase").exists()


def test_accepts_legacy_parent_directory_entries(clews_storage, tmp_path):
    path = _archive(tmp_path, [
        ("WebAPP/", ""), ("WebAPP/DataStorage/", ""),
        ("WebAPP/DataStorage/NewCase/", ""),
        ("WebAPP/DataStorage/NewCase/genData.json", '{"osy-version": "5.7"}'),
    ])
    assert CaseImporter.import_zip(str(path))[0]["status_code"] == "success"
    assert (clews_storage / "NewCase/genData.json").is_file()


@pytest.mark.parametrize("transport", ["unchunked", "chunked", "legacy"])
@pytest.mark.parametrize("prefix", ["", "WebAPP/DataStorage/"])
def test_all_upload_routes_reject_cross_case_archives(client, clews_storage, tmp_path, transport, prefix):
    existing = clews_storage / "Existing"
    existing.mkdir()
    marker = existing / "RYC.json"
    marker.write_text("original demand")
    path = _archive(tmp_path, [
        (prefix + "NewCase/genData.json", '{"osy-version": "5.7"}'),
        (prefix + "Existing/RYC.json", "replacement demand"),
    ])
    response = _post_archive(client, path.read_bytes(), transport)
    assert response.status_code == 400, response.get_json()
    assert marker.read_text() == "original demand"
    assert not (clews_storage / "NewCase").exists()


@pytest.mark.parametrize("transport", ["unchunked", "chunked", "legacy"])
@pytest.mark.parametrize("prefix", ["", "WebAPP/DataStorage/"])
def test_all_upload_routes_restore_valid_backups(client, clews_storage, tmp_path, transport, prefix):
    path = make_case_zip(tmp_path, "ValidCase", version="5.6", arc_prefix=prefix)
    # The archive's case root, not the browser filename, selects the migration target.
    response = _post_archive(client, path.read_bytes(), transport, filename="different-name.zip")
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["response"][0]["status_code"] == "success"
    data = json.loads((clews_storage / "ValidCase/genData.json").read_text())
    assert data["osy-version"] == "5.7"
    assert not (clews_storage / "different-name").exists()


@pytest.mark.parametrize("transport", ["unchunked", "legacy"])
@pytest.mark.parametrize("filename", ["Existing/RYC.json", "Variables.json", "../outside.json"])
def test_upload_filename_cannot_overwrite_model_inputs(client, clews_storage, tmp_path, transport, filename):
    existing = clews_storage / "Existing"
    existing.mkdir()
    marker = existing / "RYC.json"
    marker.write_text("original demand")
    shared = (clews_storage / "Variables.json").read_bytes()
    response = _post_archive(client, b"replacement content", transport, filename)
    assert response.status_code == 400, response.get_json()
    assert marker.read_text() == "original demand"
    assert (clews_storage / "Variables.json").read_bytes() == shared
    assert not (tmp_path / "outside.json").exists()


@pytest.mark.parametrize("chunk_id", [
    "../Existing", "Existing/nested", "..", ".", "", "/absolute", "C:drive", "bad\x00id",
])
def test_chunk_id_cannot_redirect_chunk_writes(client, clews_storage, chunk_id):
    existing = clews_storage / "Existing"
    existing.mkdir()
    marker = existing / "chunk_0"
    marker.write_text("original data")
    response = client.post("/uploadCase", data={
        "dzuuid": chunk_id, "dzchunkindex": "0", "dztotalchunkcount": "1",
        "file": (io.BytesIO(b"untrusted content"), "backup.zip"),
    }, content_type="multipart/form-data")
    assert response.status_code == 400, response.get_json()
    assert marker.read_text() == "original data"
    assert not (clews_storage / "_chunks").exists()


def test_operator_symlink_still_supports_backup_and_duplicate_refusal(client, clews_storage, tmp_path):
    external = tmp_path / "country-repository" / "PhysicalCaseName"
    external.mkdir(parents=True)
    marker = external / "genData.json"
    marker.write_text('{"osy-version": "5.7"}')
    link = clews_storage / "LinkedCase"
    link.symlink_to(external, target_is_directory=True)

    backup = client.get("/backupCase?case=LinkedCase")
    assert backup.status_code == 200
    with ZipFile(io.BytesIO(backup.data)) as zf:
        assert zf.read("LinkedCase/genData.json") == marker.read_bytes()
    response = _post_archive(client, backup.data, "chunked")
    assert response.status_code == 200
    assert response.get_json()["response"][0]["status_code"] == "warning"
    assert marker.read_text() == '{"osy-version": "5.7"}'
    assert link.is_symlink()
