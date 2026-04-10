"""
Tests for the solver and data file routes.

None of these actually run the solver. Passing a case name that doesn't exist
causes DataFile to blow up immediately when it tries to read genData.json,
which the routes catch and turn into a 404. That's enough to verify the
HTTP contract without needing GLPK or CBC installed.
"""


def test_run_wrong_method_returns_405(client):
    """Only POST should be accepted on /run."""
    resp = client.delete("/run")
    assert resp.status_code == 405


def test_run_nonexistent_case_returns_404(client):
    """
    DataFile tries to read genData.json as soon as it's created.
    If the case doesn't exist that read fails, the route catches it, and we get 404.
    """
    resp = client.post(
        "/run",
        json={"casename": "__nonexistent_xyz__", "caserunname": "REF", "solver": "glpk"},
    )
    assert resp.status_code == 404


def test_generate_data_file_wrong_method_returns_405(client):
    resp = client.delete("/generateDataFile")
    assert resp.status_code == 405


def test_generate_data_file_nonexistent_case_returns_404(client):
    resp = client.post(
        "/generateDataFile",
        json={"casename": "__nonexistent_xyz__", "caserunname": "REF"},
    )
    assert resp.status_code == 404


def test_validate_inputs_wrong_method_returns_405(client):
    resp = client.delete("/validateInputs")
    assert resp.status_code == 405


def test_validate_inputs_nonexistent_case_returns_404(client):
    resp = client.post(
        "/validateInputs",
        json={"casename": "__nonexistent_xyz__", "caserunname": "REF"},
    )
    assert resp.status_code == 404


def test_read_data_file_nonexistent_case_returns_404(client):
    resp = client.post(
        "/readDataFile",
        json={"casename": "__nonexistent_xyz__", "caserunname": "REF"},
    )
    assert resp.status_code == 404


def test_batch_run_wrong_method_returns_405(client):
    resp = client.delete("/batchRun")
    assert resp.status_code == 405
