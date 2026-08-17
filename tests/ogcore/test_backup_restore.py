"""Backing a case up and restoring it.

The restore is the interesting half. It unpacks into a staging directory and
publishes with one rename, so a restore that dies partway must leave nothing at
all: no half-case in the listing, and nothing occupying the name that would stop
the user simply trying again.
"""
import io
import json
import shutil
import zipfile

import pytest

from Classes.Base import Config
from Classes.OGCore.OGCoreCase import OGCoreCase
from Routes.OGCore import OGCoreRunRoute


def _backup(client, casename, country_id="ETH"):
    resp = client.get(
        f"/ogc/backupCase?country_id={country_id}&casename={casename}"
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_data()


def _restore(client, blob, filename="backup.zip"):
    return client.post(
        "/ogc/restoreCase",
        data={"file": (io.BytesIO(blob), filename)},
        content_type="multipart/form-data",
    )


def _case_names(client):
    return {c["casename"] for c in client.get("/ogc/getCases").get_json()}


@pytest.fixture
def backed_up(client, make_case, calibration):
    """A case with a run and some results, plus its backup zip."""
    case = make_case("c1", runs=[("base", "baseline", None)])
    (case.res_path / "base" / "results_ss.json").write_text(json.dumps({"Y": 1.5}))
    case.save_params("base", {"frisch": 0.5})
    blob = _backup(client, "c1")
    client.post("/ogc/setSession", json={"country_id": "ETH", "casename": "c1"})
    client.post("/ogc/deleteCase", json={"country_id": "ETH", "casename": "c1"})
    assert not (Config.OGC_CASES_DIR / "ETH" / "c1").exists()
    return blob


def test_backup_carries_the_case_its_runs_and_results(client, make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    (case.res_path / "base" / "results_ss.json").write_text(json.dumps({"Y": 1.5}))

    with zipfile.ZipFile(io.BytesIO(_backup(client, "c1"))) as zf:
        names = zf.namelist()

    assert "genData.json" in names, "genData.json must sit at the archive root"
    assert any(n.endswith("res/base/results_ss.json") for n in names)
    assert any(n.endswith("res/base/run_meta.json") for n in names)


def test_a_case_restores_with_its_runs_and_results(client, backed_up):
    resp = _restore(client, backed_up)

    assert resp.status_code == 200
    assert resp.get_json()["status_code"] == "success"
    assert "c1" in _case_names(client)
    run_dir = Config.OGC_CASES_DIR / "ETH" / "c1" / "res" / "base"
    assert json.loads((run_dir / "results_ss.json").read_text()) == {"Y": 1.5}
    assert client.post(
        "/ogc/getRuns", json={"country_id": "ETH", "casename": "c1"}
    ).get_json()["baseline"]["RunName"] == "base"


def test_restoring_over_an_existing_case_changes_nothing(client, backed_up):
    assert _restore(client, backed_up).status_code == 200
    marker = Config.OGC_CASES_DIR / "ETH" / "c1" / "res" / "base" / "results_ss.json"
    marker.write_text(json.dumps({"Y": 99.0}))

    resp = _restore(client, backed_up)

    assert resp.get_json()["status_code"] == "exist"
    assert json.loads(marker.read_text()) == {"Y": 99.0}, "nothing was overwritten"


def _is_the_upload_being_saved(dst):
    """True for the copy that writes the uploaded zip to its temp file.

    Werkzeug's FileStorage.save uses shutil.copyfileobj too, so a hook on it sees
    that write before extraction starts. Counting it would shift every count by one
    and, worse, make a mid-extraction snapshot fire before anything was extracted.
    """
    return str(getattr(dst, "name", "")).endswith(".zip")


def _patch_extraction_copy(monkeypatch, hook):
    """Route only the extraction copies through ``hook``; pass the upload straight."""
    real_copy = shutil.copyfileobj

    def dispatch(src, dst, *args, **kwargs):
        if _is_the_upload_being_saved(dst):
            return real_copy(src, dst, *args, **kwargs)
        return hook(real_copy, src, dst, *args, **kwargs)

    monkeypatch.setattr(OGCoreRunRoute.shutil, "copyfileobj", dispatch)


def _break_extraction_after(monkeypatch, n_files):
    """Make extraction die once it has written ``n_files``, as a full disk would.

    Returns the switch: set ``fail`` False to let a later attempt through, which is
    how the retry is tested without undoing the fixtures' own patches.
    """
    state = {"fail": True, "written": 0}

    def hook(real_copy, src, dst, *args, **kwargs):
        if state["fail"] and state["written"] >= n_files:
            raise OSError(28, "No space left on device")
        state["written"] += 1
        return real_copy(src, dst, *args, **kwargs)

    _patch_extraction_copy(monkeypatch, hook)
    return state


def test_a_restore_that_fails_partway_leaves_nothing_behind(
    client, backed_up, monkeypatch
):
    """The fix: a broken restore must not publish a half-case.

    Writing straight into the case directory used to leave the files copied so far
    sitting under the case name, which both showed up as a real case and blocked
    the retry, because restoring again found the name taken.
    """
    state = _break_extraction_after(monkeypatch, 1)

    resp = _restore(client, backed_up)

    assert resp.status_code >= 400, "a failed restore must not report success"
    assert state["written"] == 1, "one file of the backup landed before it broke"
    assert not (Config.OGC_CASES_DIR / "ETH" / "c1").exists(), "no half-case was published"
    assert "c1" not in _case_names(client), "and none appears in the listing"


def test_the_case_can_be_restored_again_after_a_failed_attempt(
    client, backed_up, monkeypatch
):
    state = _break_extraction_after(monkeypatch, 1)
    assert _restore(client, backed_up).status_code >= 400
    state["fail"] = False          # the disk has room again

    resp = _restore(client, backed_up)

    assert resp.get_json()["status_code"] == "success", (
        "the earlier failure must not leave the name occupied"
    )
    run_dir = Config.OGC_CASES_DIR / "ETH" / "c1" / "res" / "base"
    assert json.loads((run_dir / "results_ss.json").read_text()) == {"Y": 1.5}


def test_a_restore_in_flight_is_not_visible_as_a_case(client, backed_up, monkeypatch):
    """Staging happens outside the cases tree, which is what keeps it hidden.

    The restore creates the country directory before publishing into it, so the
    check is that no case appears; an empty country directory lists nothing.
    list_cases is called directly rather than through getCases, because a nested
    request is not possible inside the one being served.
    """
    seen = []

    def look_around_mid_extract(real_copy, src, dst, *args, **kwargs):
        seen.append([c["casename"] for c in OGCoreCase.list_cases()])
        return real_copy(src, dst, *args, **kwargs)

    _patch_extraction_copy(monkeypatch, look_around_mid_extract)

    assert _restore(client, backed_up).get_json()["status_code"] == "success"
    assert len(seen) > 1, "the backup has several files, so it was watched as it went"
    assert all(during == [] for during in seen), (
        "no case may appear while unpacking"
    )
    assert "c1" in _case_names(client), "and it is there once the restore finished"


def test_a_successful_restore_leaves_no_staging_directory(client, backed_up):
    assert _restore(client, backed_up).get_json()["status_code"] == "success"

    staging_root = Config.OGC_CASES_DIR.parent / "restore_tmp"
    leftovers = list(staging_root.iterdir()) if staging_root.is_dir() else []
    assert leftovers == [], f"staging directories were left behind: {leftovers}"


def test_a_failed_restore_leaves_no_staging_directory(client, backed_up, monkeypatch):
    _break_extraction_after(monkeypatch, 1)
    assert _restore(client, backed_up).status_code >= 400

    staging_root = Config.OGC_CASES_DIR.parent / "restore_tmp"
    leftovers = list(staging_root.iterdir()) if staging_root.is_dir() else []
    assert leftovers == [], f"staging directories were left behind: {leftovers}"
