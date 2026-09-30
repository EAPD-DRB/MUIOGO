"""Guards on the destructive and parameter-writing endpoints.

Deleting a baseline removes the whole case, so it needs the same session gate as
deleteCase. Parameters must not change once a run is running or queued: the worker
reads them at launch, so a later write either disagrees with a finished run's
results or slips past the dimension guard a queued run already passed.
"""
from Classes.OGCore.RunJob import RunJob


def _select(client, casename):
    """Make casename the active session case, as the UI does before deleting."""
    return client.post("/ogc/setSession", json={"country_id": "ETH", "casename": casename})


# ── deleteRun session gate ───────────────────────────────────────────────────
def test_delete_baseline_refused_without_a_session(client, make_case, calibration):
    make_case("c1", runs=[("base", "baseline", None)])
    client.post("/ogc/setSession", json={"casename": None})

    resp = client.post("/ogc/deleteRun",
                       json={"country_id": "ETH", "casename": "c1", "run_name": "base"})

    assert resp.status_code == 403
    assert "workspace" in resp.get_json()["message"].lower()


def test_delete_baseline_refused_for_a_different_session(client, make_case, calibration):
    make_case("c1", runs=[("base", "baseline", None)])
    make_case("c2", runs=[("base", "baseline", None)])
    _select(client, "c2")

    resp = client.post("/ogc/deleteRun",
                       json={"country_id": "ETH", "casename": "c1", "run_name": "base"})

    assert resp.status_code == 403


def test_delete_baseline_allowed_for_the_active_case(client, make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    _select(client, "c1")

    resp = client.post("/ogc/deleteRun",
                       json={"country_id": "ETH", "casename": "c1", "run_name": "base"})

    assert resp.status_code == 200
    assert not case.case_path.exists(), "deleting the baseline removes the case"


def test_delete_reform_does_not_need_a_session(client, make_case, calibration):
    # Only the baseline delete destroys the case, so a reform stays ungated.
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.create_run("reform1", "reform", "base", {})

    resp = client.post("/ogc/deleteRun",
                       json={"country_id": "ETH", "casename": "c1", "run_name": "reform1"})

    assert resp.status_code == 200
    assert case.case_path.exists() and not (case.res_path / "reform1").exists()


# ── parameter writes while a run is in flight ────────────────────────────────
def test_save_params_refused_while_running(client, make_case, calibration, stub_launch):
    make_case("c1", runs=[("base", "baseline", None)])
    RunJob.start("ETH", "c1", "base", False)

    resp = client.post("/ogc/saveParams",
                       json={"country_id": "ETH", "casename": "c1", "run_name": "base", "params": {"S": 40}})

    assert resp.status_code == 400
    assert "cannot be changed" in resp.get_json()["message"]


def test_save_params_refused_while_queued(client, make_case, calibration, stub_launch):
    # The queued case matters most: the dimension guard already passed at submit,
    # and the worker would read whatever is on disk when it finally launches.
    make_case("c1", runs=[("base", "baseline", None)])
    case2 = make_case("c2", runs=[("base", "baseline", None)])
    RunJob.start("ETH", "c1", "base", False)
    RunJob.start("ETH", "c2", "base", False)

    resp = client.post("/ogc/saveParams",
                       json={"country_id": "ETH", "casename": "c2", "run_name": "base", "params": {"S": 40}})

    assert resp.status_code == 400
    assert case2.get_params("base") == {}, "nothing was written"


def test_save_params_allowed_when_idle(client, make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])

    resp = client.post("/ogc/saveParams",
                       json={"country_id": "ETH", "casename": "c1", "run_name": "base", "params": {"S": 40}})

    assert resp.status_code == 200
    assert case.get_params("base") == {"S": 40}


def test_upload_tax_params_refused_while_running(
    client, make_case, calibration, stub_launch
):
    make_case("c1", runs=[("base", "baseline", None)])
    RunJob.start("ETH", "c1", "base", False)

    resp = client.post(
        "/ogc/uploadTaxParams",
        data={"country_id": "ETH", "casename": "c1", "run_name": "base"},
        content_type="multipart/form-data",
    )

    assert resp.status_code == 400
    assert "cannot be changed" in resp.get_json()["message"]
