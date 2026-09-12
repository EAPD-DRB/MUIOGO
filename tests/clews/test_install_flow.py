"""The full install pipeline over HTTP, against a real fixture country repo on disk.

No mocks in the happy path: a complete repo (manifest, vintages, SHA256SUMS, real
importable case zips) is read through source_type local_path -- the same code path
a GitHub install runs, minus the transport.
"""
import json

from Classes.Base import Config
from Classes.Clews.ClewsInstallJob import ClewsInstallJob
from Classes.Clews.CountryRegistry import CountryRegistry
from Classes.Clews.Provenance import Provenance

from .conftest import build_country_repo, wait_for_job


def _install(client, repo, **kwargs):
    body = {"source_type": "local_path", "local_path": str(repo), **kwargs}
    resp = client.post("/clews/installCountry", json=body)
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["install_id"]


def test_inspect_source_returns_the_menu(client, clews_storage, tmp_path):
    repo = build_country_repo(tmp_path)
    (clews_storage / "CaseB").mkdir()  # a name collision the menu must show

    resp = client.post("/clews/inspectSource",
                       json={"source_type": "local_path", "local_path": str(repo)})
    assert resp.status_code == 200
    menu = resp.get_json()
    assert menu["iso3"] == "TST"
    assert menu["og"] == {"key": "og-tst"}
    v2 = next(v for v in menu["vintages"] if v["id"] == "v2")
    assert v2["recommended"] is True
    assert v2["version_gate"] is None
    by_case = {c["case"]: c for c in v2["cases"]}
    assert by_case["CaseA"]["already_exists"] is False
    assert by_case["CaseB"]["already_exists"] is True


def test_inspect_source_without_manifest_refuses(client, tmp_path):
    empty = tmp_path / "no-manifest"
    empty.mkdir()
    resp = client.post("/clews/inspectSource",
                       json={"source_type": "local_path", "local_path": str(empty)})
    assert resp.status_code == 400
    assert "clews-country.json" in resp.get_json()["message"]


def test_install_recommended_case_end_to_end(client, clews_storage, tmp_path):
    repo = build_country_repo(tmp_path)
    install_id = _install(client, repo)

    job = wait_for_job(install_id)
    assert job["install_state"] == "installed", job.get("error")
    assert job["results"] == [{"case": "CaseA", "archive": "CaseA.zip",
                               "status": "installed",
                               "message": "Model CaseA have been uploaded!"}]
    # The recommended default of the recommended vintage: CaseA only.
    assert (clews_storage / "CaseA" / "genData.json").is_file()
    assert not (clews_storage / "CaseB").exists()

    # Provenance records the source, vintage, and a verified checksum.
    sidecar = Provenance.read("CaseA")
    assert sidecar["source"]["iso3"] == "TST"
    assert sidecar["source"]["vintage"] == "v2"
    assert sidecar["archive"]["verified"] is True

    # The registry indexed it without waiting for the next read.
    record = CountryRegistry.get("CaseA")
    assert record and record["managed"] is True

    # The download staging area was cleaned up.
    assert not (Config.CLEWS_DOWNLOADS_DIR / install_id).exists()

    # And the status endpoint serves the finished job.
    resp = client.get(f"/clews/getInstallStatus?install_id={install_id}")
    assert resp.get_json()["install_state"] == "installed"


def test_install_explicit_vintage_and_cases(client, clews_storage, tmp_path):
    repo = build_country_repo(tmp_path)
    install_id = _install(client, repo, vintage="v2", cases=["CaseA", "CaseB"])
    job = wait_for_job(install_id)
    assert job["install_state"] == "installed"
    assert (clews_storage / "CaseA").is_dir() and (clews_storage / "CaseB").is_dir()


def test_checksum_mismatch_installs_nothing(client, clews_storage, tmp_path):
    repo = build_country_repo(tmp_path)
    # Corrupt the archive after its checksum was published.
    archive = repo / "build_v2" / "muio" / "CaseA.zip"
    archive.write_bytes(archive.read_bytes() + b"tampered")

    install_id = _install(client, repo)
    job = wait_for_job(install_id)
    assert job["install_state"] == "failed"
    assert "Checksum mismatch" in job["error"]
    assert not (clews_storage / "CaseA").exists()


def test_existing_case_reports_already_exists(client, clews_storage, tmp_path):
    repo = build_country_repo(tmp_path)
    (clews_storage / "CaseA").mkdir()

    install_id = _install(client, repo)
    job = wait_for_job(install_id)
    # Nothing installed, nothing failed: the one selected case already exists.
    assert job["install_state"] == "failed"
    assert job["results"][0]["status"] == "already_exists"
    assert "already exists" in job["error"] or "already exist" in job["error"]


def test_version_gate_refuses_newer_vintage(client, clews_storage, tmp_path):
    repo = build_country_repo(tmp_path)
    manifest = json.loads((repo / "clews-country.json").read_text())
    manifest["vintages"][1]["muio_min_version"] = "99.0"
    (repo / "clews-country.json").write_text(json.dumps(manifest))

    install_id = _install(client, repo)
    job = wait_for_job(install_id)
    assert job["install_state"] == "failed"
    assert "99.0" in job["error"]
    assert not (clews_storage / "CaseA").exists()


def test_concurrent_install_from_same_source_is_refused(client, tmp_path, monkeypatch):
    repo = build_country_repo(tmp_path)
    # Simulate an already-running install for this source key.
    key = f"local:{repo}"
    with ClewsInstallJob._lock:
        ClewsInstallJob._active_by_key[key] = "clews_2026_01_01_001"
    try:
        resp = client.post("/clews/installCountry",
                           json={"source_type": "local_path", "local_path": str(repo)})
        assert resp.status_code == 400
        assert "already running" in resp.get_json()["message"]
    finally:
        with ClewsInstallJob._lock:
            ClewsInstallJob._active_by_key.pop(key, None)


def test_install_status_validates_id(client):
    assert client.get("/clews/getInstallStatus").status_code == 400
    assert client.get("/clews/getInstallStatus?install_id=evil").status_code == 400
    resp = client.get("/clews/getInstallStatus?install_id=clews_2020_01_01_001")
    assert resp.status_code == 404


def test_cancel_unknown_install_404s(client):
    resp = client.post("/clews/cancelInstall",
                       json={"install_id": "clews_2020_01_01_001"})
    assert resp.status_code == 404
    assert client.post("/clews/cancelInstall",
                       json={"install_id": "../etc"}).status_code == 400


def test_interrupted_job_reconciled_at_startup(clews_state):
    Config.CLEWS_INSTALL_JOBS_DIR.mkdir(parents=True, exist_ok=True)
    job = {"install_id": "clews_2026_01_01_001", "country_key": "github:x/y",
           "install_state": "installing", "install_stage": "download",
           "progress_label": "Downloading", "log_tail": []}
    (Config.CLEWS_INSTALL_JOBS_DIR / "clews_2026_01_01_001.json").write_text(
        json.dumps(job))

    ClewsInstallJob.reconcile_interrupted_jobs()
    after = ClewsInstallJob.get_status("clews_2026_01_01_001")
    assert after["install_state"] == "failed"
    assert "restart" in after["error"]


def test_cross_site_post_is_refused(client, tmp_path):
    repo = build_country_repo(tmp_path)
    resp = client.post("/clews/installCountry",
                       json={"source_type": "local_path", "local_path": str(repo)},
                       headers={"Origin": "https://evil.example"})
    assert resp.status_code == 403
