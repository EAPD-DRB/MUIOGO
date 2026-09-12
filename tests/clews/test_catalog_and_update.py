"""The country catalogue endpoint and the check-only update comparison."""
import json

from Classes.Base import Config
from Classes.Clews import CountryCatalog as cc_module
from Classes.Clews.CountryRegistry import CountryRegistry

from .conftest import build_country_repo, wait_for_job


def test_catalog_is_none_without_a_register(client, monkeypatch):
    # an empty MUIOGO_CLEWS_CATALOG_URL means "no register": nothing is fetched
    monkeypatch.setattr(Config, "CLEWS_CATALOG_URL", "")
    resp = client.get("/clews/getCountryCatalog")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["countries"] == []
    assert body["catalog_source"] == "none"


def test_catalog_live_then_cache(client, clews_state, monkeypatch):
    register = {"schema_version": 1, "repos": [
        {"key": "clews-phl", "owner": "EAPD-DRB", "repo": "CLEWs-PHL",
         "iso3": "PHL", "description": "Philippines CLEWs country model"}]}
    monkeypatch.setattr(Config, "CLEWS_CATALOG_URL", "https://example.org/register.json")
    monkeypatch.setattr(cc_module, "fetch_bytes",
                        lambda url, timeout=10: json.dumps(register).encode())

    body = client.get("/clews/getCountryCatalog").get_json()
    assert body["catalog_source"] == "live"
    entry = body["countries"][0]
    assert entry["iso3"] == "PHL"
    assert entry["repo_url"] == "https://github.com/EAPD-DRB/CLEWs-PHL"
    assert entry["install_state"] == "not_installed"

    # The register goes unreachable: the cached copy serves.
    def boom(url, timeout=10):
        raise OSError("offline")
    monkeypatch.setattr(cc_module, "fetch_bytes", boom)
    body = client.get("/clews/getCountryCatalog").get_json()
    assert body["catalog_source"] == "cache"
    assert body["countries"][0]["iso3"] == "PHL"


def test_catalog_tags_installed_countries(client, clews_storage, tmp_path, monkeypatch):
    repo = build_country_repo(tmp_path)  # iso3 TST
    resp = client.post("/clews/installCountry",
                       json={"source_type": "local_path", "local_path": str(repo)})
    wait_for_job(resp.get_json()["install_id"])

    register = {"schema_version": 1, "repos": [
        {"key": "clews-tst", "owner": "X", "repo": "CLEWs-TST", "iso3": "TST",
         "description": "Testland"}]}
    monkeypatch.setattr(Config, "CLEWS_CATALOG_URL", "https://example.org/r.json")
    monkeypatch.setattr(cc_module, "fetch_bytes",
                        lambda url, timeout=10: json.dumps(register).encode())

    entry = client.get("/clews/getCountryCatalog").get_json()["countries"][0]
    assert entry["install_state"] == "installed"
    assert entry["installed_cases"] == ["CaseA"]


def test_update_check_up_to_date_then_outdated(client, clews_storage, tmp_path):
    repo = build_country_repo(tmp_path)
    resp = client.post("/clews/installCountry",
                       json={"source_type": "local_path", "local_path": str(repo)})
    wait_for_job(resp.get_json()["install_id"])

    body = client.post("/clews/checkCountryUpdate",
                       json={"casename": "CaseA"}).get_json()
    assert body["update_available"] is False
    assert CountryRegistry.get("CaseA")["update_available"] is False

    # The source publishes a new archive for the same case.
    sums = repo / "build_v2" / "muio" / "SHA256SUMS"
    text = sums.read_text().replace(sums.read_text().split()[0], "0" * 64, 1)
    sums.write_text(text)

    body = client.post("/clews/checkCountryUpdate",
                       json={"casename": "CaseA"}).get_json()
    assert body["update_available"] is True
    record = CountryRegistry.get("CaseA")
    assert record["update_available"] is True and record["last_checked_at"]

    # ...and the flag survives a reconcile (kept across re-index).
    CountryRegistry.reconcile()
    assert CountryRegistry.get("CaseA")["update_available"] is True


def test_update_check_needs_provenance(client, clews_storage):
    (clews_storage / "Bare").mkdir()
    (clews_storage / "Bare" / "genData.json").write_text("{}")
    resp = client.post("/clews/checkCountryUpdate", json={"casename": "Bare"})
    assert resp.status_code == 404
    assert "no provenance" in resp.get_json()["message"]
