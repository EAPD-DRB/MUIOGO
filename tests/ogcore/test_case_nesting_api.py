"""The country/case pair across the HTTP layer.

Every endpoint that names a case now names its country too, so these check that
two countries can hold cases of the same name without either reaching the other.
"""
import io
import json
import uuid

import pytest

from Classes.Base import Config
from Classes.OGCore.CalibrationRegistry import CalibrationRegistry
from Classes.OGCore.OGCoreCase import OGCoreCase


@pytest.fixture
def two_countries(tmp_path):
    """USA and ETH both installed, so a case can be made under either."""
    python_path = tmp_path / "venv_python"
    python_path.write_text("")
    for cid, cname in (("USA", "United States"), ("ETH", "Ethiopia")):
        CalibrationRegistry.upsert({
            "country_id": cid, "country_name": cname, "source_type": "catalog",
            "python_path": str(python_path), "venv_path": str(tmp_path / ".venv"),
            "package_name": "ogcore", "install_state": "installed",
        })
    return python_path


def _activate(client, country_id):
    current = client.get("/ogc/getSession").get_json().get("ogccountry")
    if current == country_id:
        return
    if current:
        client.post("/ogc/setSession", json={"casename": None})
    response = client.post(
        "/ogc/setSession", json={"casename": None, "country_id": country_id}
    )
    assert response.status_code == 200


def _clear(client):
    client.post("/ogc/setSession", json={"casename": None})


def _save(client, country_id, casename, description=""):
    _activate(client, country_id)
    return client.post("/ogc/saveCase", json={"data": {
        "ogc-casename": casename,
        "country_id": country_id,
        "ogc-description": description,
    }})


def _pairs(client, **params):
    _clear(client)
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = "/ogc/getCases" + (f"?{query}" if query else "")
    return [(c["country_id"], c["casename"]) for c in client.get(url).get_json()]


# ── the collision this nesting exists to fix ────────────────────────────────
def test_two_countries_can_each_create_a_case_of_the_same_name(client, two_countries):
    assert _save(client, "USA", "Baseline", "the US one").get_json()[
        "status_code"] == "created"

    resp = _save(client, "ETH", "Baseline", "the ETH one")

    assert resp.get_json()["status_code"] == "created", (
        "the second country's case must be created, not treated as an edit"
    )
    assert sorted(_pairs(client)) == [("ETH", "Baseline"), ("USA", "Baseline")]


def test_editing_one_country_leaves_the_other_untouched(client, two_countries):
    _save(client, "USA", "Baseline", "the US one")
    _save(client, "ETH", "Baseline", "the ETH one")

    _save(client, "ETH", "Baseline", "edited")

    _clear(client)
    by_country = {c["country_id"]: c for c in client.get("/ogc/getCases").get_json()}
    assert by_country["ETH"]["description"] == "edited"
    assert by_country["USA"]["description"] == "the US one"


def test_a_case_cannot_be_saved_without_naming_its_country(client, two_countries):
    resp = client.post("/ogc/saveCase", json={"data": {
        "ogc-casename": "Baseline", "ogc-description": "no country",
    }})

    assert resp.status_code >= 400
    assert "country_id" in resp.get_json()["message"]
    assert _pairs(client) == []


def test_the_listing_can_be_narrowed_to_one_country(client, two_countries):
    _save(client, "USA", "Baseline")
    _save(client, "ETH", "Baseline")
    _save(client, "ETH", "Reform")

    assert sorted(_pairs(client, country_id="ETH")) == [
        ("ETH", "Baseline"), ("ETH", "Reform")
    ]
    assert _pairs(client, country_id="USA") == [("USA", "Baseline")]


# ── runs stay inside their own country's case ───────────────────────────────
def test_runs_of_same_named_cases_do_not_mix(client, two_countries):
    for country in ("USA", "ETH"):
        _save(client, country, "Baseline")
    _activate(client, "USA")
    client.post("/ogc/createRun", json={
        "country_id": "USA", "casename": "Baseline",
        "run_name": "us_only", "run_type": "baseline"})

    usa = client.post("/ogc/getRuns", json={
        "country_id": "USA", "casename": "Baseline"}).get_json()
    _activate(client, "ETH")
    eth = client.post("/ogc/getRuns", json={
        "country_id": "ETH", "casename": "Baseline"}).get_json()

    assert usa["baseline"]["RunName"] == "us_only"
    assert eth["baseline"] is None, "the other country's case has no runs"


def test_params_of_same_named_runs_stay_apart(client, two_countries):
    for country, frisch in (("USA", 0.1), ("ETH", 0.9)):
        _save(client, country, "Baseline")
        client.post("/ogc/createRun", json={
            "country_id": country, "casename": "Baseline",
            "run_name": "base", "run_type": "baseline"})
        client.post("/ogc/saveParams", json={
            "country_id": country, "casename": "Baseline",
            "run_name": "base", "params": {"frisch": frisch}})

    def read(country):
        _activate(client, country)
        return client.post("/ogc/getParams", json={
            "country_id": country, "casename": "Baseline",
            "run_name": "base"}).get_json()

    assert read("USA") == {"frisch": 0.1}
    assert read("ETH") == {"frisch": 0.9}


# ── the session carries both halves ─────────────────────────────────────────
def test_the_session_records_the_country_with_the_case(client, two_countries):
    _save(client, "ETH", "Baseline")

    resp = client.post("/ogc/setSession", json={
        "country_id": "ETH", "casename": "Baseline"})

    assert resp.get_json() == {"ogccase": "Baseline", "ogccountry": "ETH"}
    assert client.get("/ogc/getSession").get_json() == {
        "ogccase": "Baseline", "ogccountry": "ETH"}


def test_the_session_will_not_point_at_a_case_the_country_does_not_have(
    client, two_countries
):
    _save(client, "ETH", "Baseline")
    _clear(client)
    _activate(client, "USA")

    resp = client.post("/ogc/setSession", json={
        "country_id": "USA", "casename": "Baseline"})

    assert resp.status_code == 404


def test_clearing_the_session_clears_both_halves(client, two_countries):
    _save(client, "ETH", "Baseline")
    client.post("/ogc/setSession", json={"country_id": "ETH", "casename": "Baseline"})

    client.post("/ogc/setSession", json={"casename": None})

    assert client.get("/ogc/getSession").get_json() == {
        "ogccase": None, "ogccountry": None}


def test_deleting_needs_the_session_to_match_both_halves(client, two_countries):
    _save(client, "USA", "Baseline")
    _save(client, "ETH", "Baseline")
    client.post("/ogc/setSession", json={"country_id": "ETH", "casename": "Baseline"})

    resp = client.post("/ogc/deleteCase", json={
        "country_id": "USA", "casename": "Baseline"})

    assert resp.status_code == 403
    assert sorted(_pairs(client)) == [("ETH", "Baseline"), ("USA", "Baseline")]


def test_deleting_removes_only_the_named_country_s_case(client, two_countries):
    _save(client, "USA", "Baseline")
    _save(client, "ETH", "Baseline")
    client.post("/ogc/setSession", json={"country_id": "ETH", "casename": "Baseline"})

    resp = client.post("/ogc/deleteCase", json={
        "country_id": "ETH", "casename": "Baseline"})

    assert resp.status_code == 200
    assert _pairs(client) == [("USA", "Baseline")]


# ── backup and restore ──────────────────────────────────────────────────────
def _restore(client, blob, **form):
    data = {"file": (io.BytesIO(blob), "backup.zip")}
    data.update(form)
    return client.post("/ogc/restoreCase", data=data,
                       content_type="multipart/form-data")


def test_a_case_restores_into_the_country_it_came_from(client, two_countries):
    _save(client, "ETH", "Baseline", "the ETH one")
    blob = client.get(
        "/ogc/backupCase?country_id=ETH&casename=Baseline").get_data()
    client.post("/ogc/setSession", json={"country_id": "ETH", "casename": "Baseline"})
    client.post("/ogc/deleteCase", json={"country_id": "ETH", "casename": "Baseline"})

    assert _restore(client, blob).get_json()["status_code"] == "success"

    assert _pairs(client) == [("ETH", "Baseline")]
    assert (Config.OGC_CASES_DIR / "ETH" / "Baseline" / "genData.json").is_file()


def test_a_restore_does_not_collide_with_the_same_name_elsewhere(client, two_countries):
    _save(client, "ETH", "Baseline", "the ETH one")
    blob = client.get(
        "/ogc/backupCase?country_id=ETH&casename=Baseline").get_data()
    client.post("/ogc/setSession", json={"country_id": "ETH", "casename": "Baseline"})
    client.post("/ogc/deleteCase", json={"country_id": "ETH", "casename": "Baseline"})
    _save(client, "USA", "Baseline", "the US one")

    assert _restore(client, blob).get_json()["status_code"] == "success"

    _clear(client)
    by_country = {c["country_id"]: c for c in client.get("/ogc/getCases").get_json()}
    assert by_country["ETH"]["description"] == "the ETH one"
    assert by_country["USA"]["description"] == "the US one"


def _flat_backup(casename, **gen_extra):
    """A backup zip in the pre-nesting shape, with no country recorded."""
    import zipfile

    buf = io.BytesIO()
    gd = {"ogc-casename": casename, "ogc-description": "old", "ogc-runs": [],
          "ogc-version": "1.0"}
    gd.update(gen_extra)
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("genData.json", json.dumps(gd))
    return buf.getvalue()


def test_a_backup_with_no_country_is_refused_until_one_is_given(client, two_countries):
    blob = _flat_backup("Legacy")

    resp = _restore(client, blob)

    assert resp.status_code >= 400
    assert "country" in resp.get_json()["message"].lower()
    assert _pairs(client) == []


def test_a_backup_with_no_country_restores_into_the_one_supplied(client, two_countries):
    blob = _flat_backup("Legacy")

    resp = _restore(client, blob, country_id="ETH")

    assert resp.get_json()["status_code"] == "success"
    assert _pairs(client) == [("ETH", "Legacy")]
    restored = Config.OGC_CASES_DIR / "ETH" / "Legacy" / "genData.json"
    assert json.loads(restored.read_text())["country_id"] == "ETH"


def test_restoring_over_an_existing_case_still_refuses(client, two_countries):
    _save(client, "ETH", "Baseline", "live")
    blob = client.get(
        "/ogc/backupCase?country_id=ETH&casename=Baseline").get_data()

    resp = _restore(client, blob)

    assert resp.get_json()["status_code"] == "exist"
    by_country = {c["country_id"]: c for c in client.get("/ogc/getCases").get_json()}
    assert by_country["ETH"]["description"] == "live"


# ── refusals ────────────────────────────────────────────────────────────────
def test_a_country_id_that_escapes_the_cases_directory_is_refused(
    client, two_countries
):
    resp = client.post("/ogc/getRuns", json={
        "country_id": "../..", "casename": "Baseline"})

    assert resp.status_code >= 400


def test_naming_a_country_that_does_not_hold_the_case_is_a_404(client, two_countries):
    _save(client, "ETH", "Baseline")
    _clear(client)
    _activate(client, "USA")

    resp = client.post("/ogc/getRuns", json={
        "country_id": "USA", "casename": "Baseline"})

    assert resp.status_code == 404


def test_endpoints_say_which_field_is_missing(client, two_countries):
    resp = client.post("/ogc/getRuns", json={"casename": "Baseline"})

    assert resp.status_code >= 400
    assert "country_id" in resp.get_json()["message"]
