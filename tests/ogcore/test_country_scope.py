"""Minimal backend country-workspace isolation for case-addressed routes."""

from Classes.OGCore.CalibrationRegistry import CalibrationRegistry


def _install_zaf(tmp_path):
    python_path = tmp_path / "zaf_python"
    python_path.write_text("")
    CalibrationRegistry.upsert({
        "country_id": "ZAF",
        "country_name": "South Africa",
        "source_type": "catalog",
        "python_path": str(python_path),
        "venv_path": str(tmp_path / "zaf_venv"),
        "package_name": "ogcore",
        "install_state": "installed",
    })


def test_active_country_blocks_foreign_run_reads_and_writes(
    client, make_case, calibration, tmp_path
):
    _install_zaf(tmp_path)
    make_case("eth_case", country_id="ETH", runs=[("base", "baseline", None)])
    zaf = make_case("zaf_case", country_id="ZAF", runs=[("base", "baseline", None)])

    activated = client.post(
        "/ogc/setSession", json={"casename": None, "country_id": "ETH"}
    )
    assert activated.status_code == 200

    read = client.post("/ogc/getRuns", json={"casename": "zaf_case"})
    params = client.post(
        "/ogc/getParams", json={"casename": "zaf_case", "run_name": "base"}
    )
    write = client.post(
        "/ogc/saveParams",
        json={"casename": "zaf_case", "run_name": "base", "params": {"S": 40}},
    )
    execute = client.post(
        "/ogc/run",
        json={"casename": "zaf_case", "run_name": "base", "time_path": False},
    )

    assert {read.status_code, params.status_code, write.status_code, execute.status_code} == {403}
    assert zaf.get_params("base") == {}


def test_clearing_country_allows_an_explicit_workspace_switch(
    client, make_case, calibration, tmp_path
):
    _install_zaf(tmp_path)
    make_case("eth_case", country_id="ETH", runs=[("base", "baseline", None)])
    make_case("zaf_case", country_id="ZAF", runs=[("base", "baseline", None)])
    client.post("/ogc/setSession", json={"casename": None, "country_id": "ETH"})

    blocked = client.post("/ogc/setSession", json={"casename": "zaf_case"})
    assert blocked.status_code == 403

    client.post("/ogc/setSession", json={"casename": None})
    switched = client.post(
        "/ogc/setSession", json={"casename": None, "country_id": "ZAF"}
    )
    read = client.post("/ogc/getRuns", json={"casename": "zaf_case"})

    assert switched.status_code == 200
    assert switched.get_json()["ogccountry"] == "ZAF"
    assert read.status_code == 200


def test_selecting_a_case_records_its_country(client, make_case, calibration):
    make_case("eth_case", country_id="ETH", runs=[("base", "baseline", None)])

    selected = client.post("/ogc/setSession", json={"casename": "eth_case"})
    current = client.get("/ogc/getSession").get_json()

    assert selected.status_code == 200
    assert current == {"ogccase": "eth_case", "ogccountry": "ETH"}


def test_identical_case_names_cannot_coexist_across_countries(
    client, calibration, tmp_path
):
    _install_zaf(tmp_path)
    first = client.post("/ogc/saveCase", json={
        "data": {"ogc-casename": "same", "country_id": "ETH"}
    })
    assert first.status_code == 200
    client.post("/ogc/setSession", json={"casename": None})

    second = client.post("/ogc/saveCase", json={
        "data": {"ogc-casename": "same", "country_id": "ZAF"}
    })

    assert second.status_code == 403
    assert "Open that country workspace" in second.get_json()["message"]


def test_deleting_active_case_preserves_country_scope(
    client, make_case, calibration, tmp_path
):
    _install_zaf(tmp_path)
    make_case("eth_case", country_id="ETH", runs=[("base", "baseline", None)])
    make_case("zaf_case", country_id="ZAF", runs=[("base", "baseline", None)])
    client.post("/ogc/setSession", json={"casename": "eth_case"})

    deleted = client.post("/ogc/deleteCase", json={"casename": "eth_case"})
    current = client.get("/ogc/getSession").get_json()
    foreign = client.post("/ogc/getRuns", json={"casename": "zaf_case"})
    visible = client.get("/ogc/getCases").get_json()

    assert deleted.status_code == 200
    assert current == {"ogccase": None, "ogccountry": "ETH"}
    assert foreign.status_code == 403
    assert visible == []
