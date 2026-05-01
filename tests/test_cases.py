"""
Tests for the case management routes.

Covers /getCases, /getResultCSV, /resultsExists, and /deleteCaseRun.
Focuses on what the routes do when things go wrong -- missing cases,
empty inputs, wrong HTTP methods.
"""


def test_get_cases_returns_200(client):
    resp = client.get("/getCases")
    assert resp.status_code == 200


def test_get_cases_returns_list(client):
    """Should always return a list -- empty is fine, but not null and not an error."""
    resp = client.get("/getCases")
    assert isinstance(resp.get_json(), list)


def test_get_cases_wrong_method_returns_405(client):
    resp = client.post("/getCases")
    assert resp.status_code == 405


def test_get_result_csv_nonexistent_case_returns_empty_list(client):
    """
    If the run folder doesn't exist yet, getResultCSV should return an empty
    list rather than an error. The route checks isdir() first before trying to scan.
    """
    resp = client.post(
        "/getResultCSV",
        json={"casename": "__nonexistent_xyz__", "caserunname": "REF"},
    )
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_results_exists_nonexistent_case_returns_404(client):
    """
    resultsExists reads resData.json for the case. If the case doesn't exist,
    that read fails with IOError and the route returns 404.
    """
    resp = client.post(
        "/resultsExists",
        json={"casename": "__nonexistent_xyz__"},
    )
    assert resp.status_code == 404


def test_delete_case_run_empty_casename_returns_400(client):
    """
    The route checks the casename before touching the filesystem.
    An empty string should be caught immediately and return 400.
    """
    resp = client.post(
        "/deleteCaseRun",
        json={"casename": "", "caserunname": "REF", "resultsOnly": False},
    )
    assert resp.status_code == 400


def test_delete_case_run_nonexistent_case_returns_404(client):
    """
    If the case directory doesn't exist, shutil.rmtree raises FileNotFoundError.
    The route catches that and returns 404.
    """
    resp = client.post(
        "/deleteCaseRun",
        json={"casename": "__nonexistent_xyz__", "caserunname": "REF", "resultsOnly": False},
    )
    assert resp.status_code == 404
