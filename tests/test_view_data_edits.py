"""Cross-parameter edits must identify one cell, including modes and constraints."""

import copy
import json

import pytest

from Classes.Base import Config
from Classes.Case.OsemosysClass import Osemosys
from tests.view_data_fixtures import CASE_NAME, make_view_data_case


@pytest.fixture
def edit_case(tmp_path, monkeypatch):
    case = make_view_data_case(tmp_path / "DataStorage")
    monkeypatch.setattr(Config, "DATA_STORAGE", case.parent)
    return case


def annual_payload(group="RYTM", param="VC", **changes):
    return {
        "casename": CASE_NAME, "year": "2030", "ScId": "SC_0",
        "groupId": group, "paramId": param,
        "TechId": None, "CommId": None, "EmisId": None,
        "Timeslice": None, "MoId": None, "ConId": None, "value": 0,
        **changes,
    }


def snapshot(case):
    return {str(p.relative_to(case.parent)): p.read_bytes()
            for p in case.parent.rglob("*.json")}


@pytest.mark.parametrize("group,param,selectors", [
    ("RYT", "CC", {"TechId": "T1"}),
    ("RYC", "SAD", {"CommId": "C1"}),
    ("RYE", "EP", {"EmisId": "E1"}),
    ("RYTM", "VC", {"TechId": "T1", "MoId": "1"}),
    ("RYTC", "INCR", {"TechId": "T1", "CommId": "C1"}),
    ("RYTCM", "OAR", {"TechId": "T1", "CommId": "C1", "MoId": 1}),
    ("RYTEM", "EAR", {"TechId": "T1", "EmisId": "E1", "MoId": 1}),
    ("RYTTs", "CF", {"TechId": "T1", "Timeslice": "TS1"}),
    ("RYCTs", "SDP", {"CommId": "C1", "Timeslice": "TS1"}),
    ("RYTCn", "CAM", {"TechId": "T1", "ConId": "CN1"}),
])
@pytest.mark.parametrize("scenario", ["SC_0", "SC_1"])
def test_annual_edit_changes_only_the_identified_cell(client, edit_case, group, param, selectors, scenario):
    before = snapshot(edit_case)
    path = edit_case / f"{group}.json"
    expected = json.loads(path.read_text())
    expected[param][scenario][0]["2030"] = 0

    response = client.post("/updateViewData", json=annual_payload(group, param, ScId=scenario, **selectors))

    assert response.status_code == 200, response.get_json()
    assert json.loads(path.read_text()) == expected
    after = snapshot(edit_case)
    key = f"{CASE_NAME}/{group}.json"
    assert {k: v for k, v in after.items() if k != key} == {k: v for k, v in before.items() if k != key}


@pytest.mark.parametrize("group,param,selectors,key", [
    ("RT", "OL", {"techId": "T1", "emisId": None}, "T1"),
    ("RE", "MPEL", {"techId": None, "emisId": "E1"}, "E1"),
])
@pytest.mark.parametrize("scenario", ["SC_0", "SC_1"])
def test_non_yearly_edit_accepts_unused_null_id(client, edit_case, group, param, selectors, key, scenario):
    path = edit_case / f"{group}.json"
    expected = json.loads(path.read_text())
    expected[param][scenario][0][key] = 25
    response = client.post("/updateTEViewData", json={
        "casename": CASE_NAME, "groupId": group, "paramId": param,
        "scId": scenario, "value": 25, **selectors,
    })
    assert response.status_code == 200, response.get_json()
    assert json.loads(path.read_text()) == expected


@pytest.mark.parametrize("changes", [
    {}, {"TechId": "T1"}, {"TechId": "unknown", "MoId": 1},
    {"TechId": "T1", "MoId": 1, "CommId": "C1"},
    {"TechId": "T1", "MoId": 1, "ConId": "CN1"},
    *({"TechId": "T1", "MoId": mode} for mode in (0, -1, True, 1.5, "1.0", [], {})),
    *({"TechId": "T1", "MoId": 1, "value": value} for value in (None, True, "12", [], float("nan"), float("inf"))),
    {"TechId": "T1", "MoId": 1, "year": "1999"},
    {"TechId": "T1", "MoId": 1, "year": []},
    {"TechId": "T1", "MoId": 1, "ScId": "missing"},
    {"TechId": "T1", "MoId": 1, "ScId": []},
    {"TechId": "T1", "MoId": 1, "paramId": "missing"},
    {"TechId": "T1", "MoId": 1, "paramId": []},
    {"TechId": "T1", "MoId": 1, "groupId": "../outside"},
    {"TechId": "T1", "MoId": 1, "groupId": []},
    {"TechId": "T1", "MoId": 1, "casename": "../outside"},
    {"TechId": "T1", "MoId": 1, "casename": []},
])
def test_invalid_annual_edits_do_not_write(client, edit_case, changes):
    before = snapshot(edit_case)
    response = client.post("/updateViewData", json=annual_payload(**changes))
    assert response.status_code == 400, response.get_json()
    assert snapshot(edit_case) == before


@pytest.mark.parametrize("endpoint", ["/updateViewData", "/updateTEViewData"])
@pytest.mark.parametrize("body", [[], "invalid", 1, True])
def test_edit_body_must_be_an_object(client, edit_case, endpoint, body):
    before = snapshot(edit_case)
    assert client.post(endpoint, json=body).status_code == 400
    assert snapshot(edit_case) == before


def test_duplicate_source_rows_are_rejected_before_writing(client, edit_case):
    path = edit_case / "RYTM.json"
    data = json.loads(path.read_text())
    data["VC"]["SC_0"].append(copy.deepcopy(data["VC"]["SC_0"][0]))
    path.write_text(json.dumps(data))
    before = snapshot(edit_case)
    response = client.post("/updateViewData", json=annual_payload(TechId="T1", MoId=1))
    assert response.status_code == 400
    assert snapshot(edit_case) == before


def test_missing_year_cell_is_not_created(client, edit_case):
    path = edit_case / "RYTM.json"
    data = json.loads(path.read_text())
    del data["VC"]["SC_0"][0]["2030"]
    path.write_text(json.dumps(data))
    before = snapshot(edit_case)
    assert client.post("/updateViewData", json=annual_payload(TechId="T1", MoId=1)).status_code == 400
    assert snapshot(edit_case) == before


def test_scalar_edit_without_entity_cannot_update_every_key(client, edit_case):
    before = snapshot(edit_case)
    response = client.post("/updateTEViewData", json={
        "casename": CASE_NAME, "groupId": "RT", "paramId": "OL",
        "scId": "SC_0", "techId": None, "emisId": None, "value": 25,
    })
    assert response.status_code == 400
    assert snapshot(edit_case) == before


def test_editor_fix_does_not_relax_other_routes(client):
    response = client.post("/generateDataFile", json={"casename": None, "caserunname": "REF"})
    assert response.status_code == 400
    assert "cannot be null" in response.get_json()["error"]


def test_service_rejects_a_case_identity_mismatch(edit_case):
    before = snapshot(edit_case)
    with pytest.raises(ValueError, match="Case"):
        Osemosys(CASE_NAME).updateTEViewData("another case", "SC_0", "RT", "OL", "T1", None, 25)
    assert snapshot(edit_case) == before
