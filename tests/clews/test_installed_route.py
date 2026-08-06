"""/clews/getInstalledCountries: the reconciled installed list over HTTP."""
import json

from Classes.Case.CaseImporter import CaseImporter

from .conftest import make_case_zip, minimal_gendata


def test_empty_storage_returns_empty_list(client):
    resp = client.get("/clews/getInstalledCountries")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status_code"] == "success"
    assert body["cases"] == []


def test_lists_managed_and_unmanaged_cases(client, clews_storage, tmp_path):
    # One tracked install...
    zip_path = make_case_zip(tmp_path, "Managed", version="5.6")
    CaseImporter.import_zip(str(zip_path), source={"type": "repo_url", "iso3": "PHL"})
    # ...and one case dropped in by hand.
    hand = clews_storage / "ByHand"
    hand.mkdir()
    (hand / "genData.json").write_text(json.dumps(minimal_gendata("ByHand", "5.0")))

    resp = client.get("/clews/getInstalledCountries")
    body = resp.get_json()
    by_name = {c["casename"]: c for c in body["cases"]}
    assert by_name["Managed"]["managed"] is True
    assert by_name["ByHand"]["managed"] is False
    assert sorted(body["reconcile"]["adopted"]) == ["Managed"]
    assert sorted(body["reconcile"]["unmanaged"]) == ["ByHand"]

    # A second read reports a quiet reconcile.
    again = client.get("/clews/getInstalledCountries").get_json()
    assert again["reconcile"] == {"adopted": [], "unmanaged": [], "removed": [],
                                  "total": 2}


def test_wrong_method_returns_405(client):
    resp = client.post("/clews/getInstalledCountries")
    assert resp.status_code == 405
