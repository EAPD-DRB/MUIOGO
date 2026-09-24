"""
Tests for path traversal protection in DataFileRoute.py.

Every route that accepts casename or caserunname from the request body must
reject path traversal payloads that escape DATA_STORAGE with a 400 status.

Config.validate_path resolves the full path and checks it stays under
DATA_STORAGE.  Traversals that *stay inside* DATA_STORAGE are not flagged
(they just point at a different case — normal filesystem behaviour).  Only
traversals that *escape* the storage root are rejected.

The Osemosys constructor validates casename, but caserunname was historically
unchecked — these tests verify the new _validate_case_inputs guard.
"""

import pytest

# ---------------------------------------------------------------------------
# Traversal payloads that ESCAPE DATA_STORAGE  (the real attacks)
# ---------------------------------------------------------------------------
# DATA_STORAGE = <project>/WebAPP/DataStorage
# casename is joined directly:          DataStorage/<casename>
# caserunname is joined as:             DataStorage/<casename>/res/<caserunname>
#
# To escape DataStorage from the casename position we need ../../
# To escape DataStorage from the caserunname position we need ../../../../
# (because the path is DataStorage/<case>/res/<caserunname>)

ESCAPING_CASENAMES = [
    "../../etc/passwd",
    "../../../etc/shadow",
    "valid_case/../../../etc",
]

# These escape DataStorage from the caserunname position
# resolved path: DataStorage/safe_case/res/../../../../tmp -> /tmp (outside DataStorage)
ESCAPING_CASERUNNAMES = [
    "../../../../tmp/evil",
    "../../../../../etc/shadow",
    "run/../../../../tmp/hack",
]

# Null byte payloads — blocked by explicit \x00 check in validate_path
NULL_BYTE_CASENAMES = [
    "case\x00injected",
]

NULL_BYTE_CASERUNNAMES = [
    "run\x00injected",
]


# ---------------------------------------------------------------------------
# POST routes that accept casename — traversal MUST be blocked (400)
# ---------------------------------------------------------------------------
class TestCasenameTraversal:
    """Routes must reject casename payloads that escape DATA_STORAGE."""

    @pytest.mark.parametrize("payload", ESCAPING_CASENAMES + NULL_BYTE_CASENAMES)
    def test_generateDataFile_rejects_bad_casename(self, client, payload):
        resp = client.post("/generateDataFile", json={
            "casename": payload,
            "caserunname": "safe_run"
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASENAMES + NULL_BYTE_CASENAMES)
    def test_createCaseRun_rejects_bad_casename(self, client, payload):
        resp = client.post("/createCaseRun", json={
            "casename": payload,
            "caserunname": "safe_run",
            "data": {}
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASENAMES + NULL_BYTE_CASENAMES)
    def test_updateCaseRun_rejects_bad_casename(self, client, payload):
        resp = client.post("/updateCaseRun", json={
            "casename": payload,
            "caserunname": "safe_run",
            "oldcaserunname": "old_run",
            "data": {}
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASENAMES + NULL_BYTE_CASENAMES)
    def test_deleteCaseRun_rejects_bad_casename(self, client, payload):
        resp = client.post("/deleteCaseRun", json={
            "casename": payload,
            "caserunname": "safe_run",
            "resultsOnly": False
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASENAMES + NULL_BYTE_CASENAMES)
    def test_deleteScenarioCaseRuns_rejects_bad_casename(self, client, payload):
        resp = client.post("/deleteScenarioCaseRuns", json={
            "scenarioId": "sc1",
            "casename": payload
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASENAMES + NULL_BYTE_CASENAMES)
    def test_saveView_rejects_bad_casename(self, client, payload):
        resp = client.post("/saveView", json={
            "casename": payload,
            "param": "test",
            "data": {}
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASENAMES + NULL_BYTE_CASENAMES)
    def test_updateViews_rejects_bad_casename(self, client, payload):
        resp = client.post("/updateViews", json={
            "casename": payload,
            "param": "test",
            "data": {}
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASENAMES + NULL_BYTE_CASENAMES)
    def test_readDataFile_rejects_bad_casename(self, client, payload):
        resp = client.post("/readDataFile", json={
            "casename": payload,
            "caserunname": "safe_run"
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASENAMES + NULL_BYTE_CASENAMES)
    def test_validateInputs_rejects_bad_casename(self, client, payload):
        resp = client.post("/validateInputs", json={
            "casename": payload,
            "caserunname": "safe_run"
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASENAMES + NULL_BYTE_CASENAMES)
    def test_run_rejects_bad_casename(self, client, payload):
        resp = client.post("/run", json={
            "casename": payload,
            "caserunname": "safe_run",
            "solver": "cbc"
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASENAMES + NULL_BYTE_CASENAMES)
    def test_batchRun_rejects_bad_modelname(self, client, payload):
        resp = client.post("/batchRun", json={
            "modelname": payload,
            "cases": ["run1"]
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASENAMES + NULL_BYTE_CASENAMES)
    def test_cleanUp_rejects_bad_modelname(self, client, payload):
        resp = client.post("/cleanUp", json={
            "modelname": payload
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST routes: traversal in caserunname — the main gap this PR fixes
# ---------------------------------------------------------------------------
class TestCaserunnameTraversal:
    """Routes must reject caserunname payloads that escape DATA_STORAGE.
    This was the primary vulnerability: casename was validated by the
    Osemosys constructor, but caserunname was never checked."""

    @pytest.mark.parametrize("payload", ESCAPING_CASERUNNAMES + NULL_BYTE_CASERUNNAMES)
    def test_generateDataFile_rejects_bad_caserunname(self, client, payload):
        resp = client.post("/generateDataFile", json={
            "casename": "safe_case",
            "caserunname": payload
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASERUNNAMES + NULL_BYTE_CASERUNNAMES)
    def test_createCaseRun_rejects_bad_caserunname(self, client, payload):
        resp = client.post("/createCaseRun", json={
            "casename": "safe_case",
            "caserunname": payload,
            "data": {}
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASERUNNAMES + NULL_BYTE_CASERUNNAMES)
    def test_updateCaseRun_rejects_bad_caserunname(self, client, payload):
        resp = client.post("/updateCaseRun", json={
            "casename": "safe_case",
            "caserunname": payload,
            "oldcaserunname": "old_run",
            "data": {}
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASERUNNAMES + NULL_BYTE_CASERUNNAMES)
    def test_updateCaseRun_rejects_bad_oldcaserunname(self, client, payload):
        resp = client.post("/updateCaseRun", json={
            "casename": "safe_case",
            "caserunname": "safe_run",
            "oldcaserunname": payload,
            "data": {}
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASERUNNAMES + NULL_BYTE_CASERUNNAMES)
    def test_deleteCaseRun_rejects_bad_caserunname(self, client, payload):
        resp = client.post("/deleteCaseRun", json={
            "casename": "safe_case",
            "caserunname": payload,
            "resultsOnly": False
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASERUNNAMES + NULL_BYTE_CASERUNNAMES)
    def test_readDataFile_rejects_bad_caserunname(self, client, payload):
        resp = client.post("/readDataFile", json={
            "casename": "safe_case",
            "caserunname": payload
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASERUNNAMES + NULL_BYTE_CASERUNNAMES)
    def test_validateInputs_rejects_bad_caserunname(self, client, payload):
        resp = client.post("/validateInputs", json={
            "casename": "safe_case",
            "caserunname": payload
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASERUNNAMES + NULL_BYTE_CASERUNNAMES)
    def test_run_rejects_bad_caserunname(self, client, payload):
        resp = client.post("/run", json={
            "casename": "safe_case",
            "caserunname": payload,
            "solver": "cbc"
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("payload", ESCAPING_CASERUNNAMES + NULL_BYTE_CASERUNNAMES)
    def test_batchRun_rejects_bad_caserunname_in_list(self, client, payload):
        resp = client.post("/batchRun", json={
            "modelname": "safe_case",
            "cases": [payload]
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Solver whitelist
# ---------------------------------------------------------------------------
class TestSolverWhitelist:
    """The /run endpoint should reject solver values outside the allowed set."""

    @pytest.mark.parametrize("solver", [
        "bash",
        "rm -rf /",
        "python",
        "'; DROP TABLE--",
        "",
        "GLPK; curl evil.com",
    ])
    def test_run_rejects_invalid_solver(self, client, solver):
        resp = client.post("/run", json={
            "casename": "safe_case",
            "caserunname": "safe_run",
            "solver": solver
        })
        assert resp.status_code == 400

    def test_run_does_not_reject_valid_solver_cbc(self, client):
        """cbc is valid so the request shouldn't fail at the solver stage.
        It will fail later (404 — no such case on disk), but NOT with 400
        for the solver check."""
        resp = client.post("/run", json={
            "casename": "safe_case",
            "caserunname": "safe_run",
            "solver": "cbc"
        })
        # Must not be 400 with 'Invalid solver' — the next failure is
        # 404 (IOError from DataFile constructor reading nonexistent case).
        assert resp.status_code != 200  # won't succeed — case doesn't exist
        data = resp.get_json(force=True)
        if resp.status_code == 400:
            # If it's 400, make sure it's not the solver check
            assert "solver" not in str(data).lower()

    def test_run_does_not_reject_valid_solver_glpk(self, client):
        resp = client.post("/run", json={
            "casename": "safe_case",
            "caserunname": "safe_run",
            "solver": "glpk"
        })
        assert resp.status_code != 200
        data = resp.get_json(force=True)
        if resp.status_code == 400:
            assert "solver" not in str(data).lower()


# ---------------------------------------------------------------------------
# Null byte injection  (explicit \x00 check in Config.validate_path)
# ---------------------------------------------------------------------------
class TestNullByteInjection:
    """Null bytes are a classic bypass vector — Config.validate_path blocks them."""

    def test_casename_with_null_byte(self, client):
        resp = client.post("/generateDataFile", json={
            "casename": "valid\x00../../etc/passwd",
            "caserunname": "run1"
        })
        assert resp.status_code == 400

    def test_caserunname_with_null_byte(self, client):
        resp = client.post("/run", json={
            "casename": "safe",
            "caserunname": "run\x00../../etc/passwd",
            "solver": "cbc"
        })
        assert resp.status_code == 400
