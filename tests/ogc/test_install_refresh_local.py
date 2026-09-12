"""Updating a calibration registered from a local folder (issue #543).

MUIOGO used to refuse every automatic update of a local_path record, and a check
left the stored commit at the installed version even after the clone had been
pulled by hand. Now a check records what is actually checked out and whether the
clone is safe to pull (tracked files clean, branch tracking its remote), and an
update is allowed exactly in that case. Uses real git repositories in tmp_path.
"""
import subprocess
import time

from Classes.OGCore.CalibrationRegistry import CalibrationRegistry
from Classes.OGCore.InstallJob import InstallJob
from Classes.OGCore.Installer import Installer


def _git(args, cwd):
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false",
         *args],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    ).stdout.strip()


def _clone_behind_origin(tmp_path):
    """A bare origin, a clone of it, then one more commit on origin only."""
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(["init", "--bare", "-q", "-b", "main"], origin)
    seed = tmp_path / "seed"
    _git(["clone", "-q", str(origin), str(seed)], tmp_path)
    (seed / "pyproject.toml").write_text('[project]\nname = "ogeth"\nversion = "0.1.0"\n')
    _git(["add", "-A"], seed)
    _git(["commit", "-q", "-m", "one"], seed)
    _git(["push", "-q", "origin", "HEAD:main"], seed)
    clone = tmp_path / "OG-ETH"
    _git(["clone", "-q", str(origin), str(clone)], tmp_path)
    (seed / "pyproject.toml").write_text('[project]\nname = "ogeth"\nversion = "0.2.0"\n')
    _git(["commit", "-q", "-am", "two"], seed)
    _git(["push", "-q", "origin", "HEAD:main"], seed)
    return clone


def _register_local(clone):
    CalibrationRegistry.upsert({
        "country_id": "ETH", "country_name": "Ethiopia", "source_type": "local_path",
        "local_path": str(clone), "venv_path": str(clone / ".venv"),
        "python_path": str(clone / ".venv/bin/python"), "package_name": "ogeth",
        "repo_url": Installer.git_remote_url(clone), "commit_sha": "stale",
        "install_state": "installed", "installed_at": "2026-01-01T00:00:00Z",
    })


def _check(client):
    resp = client.post("/ogc/refreshCalibration",
                       json={"country_id": "ETH", "check_only": True})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


def _apply(client):
    return client.post("/ogc/refreshCalibration",
                       json={"country_id": "ETH", "check_only": False})


def test_check_records_checked_out_commit_and_updatable(client, tmp_path):
    clone = _clone_behind_origin(tmp_path)
    _register_local(clone)

    body = _check(client)

    assert body["install_state"] == "update_available"
    assert body["updatable"] is True and body["update_blocked_reason"] is None
    record = CalibrationRegistry.get("ETH")
    assert record["commit_sha"] == Installer.git_head_sha(clone), \
        "the record says what is checked out, not what was installed"
    assert record["updatable"] is True


def test_check_after_a_manual_pull_moves_the_recorded_commit(client, tmp_path):
    clone = _clone_behind_origin(tmp_path)
    _register_local(clone)
    _git(["pull", "-q", "--ff-only"], clone)

    body = _check(client)

    assert body["install_state"] == "installed"
    assert CalibrationRegistry.get("ETH")["commit_sha"] == Installer.git_head_sha(clone)


def test_clean_tracking_clone_can_be_updated(client, tmp_path, monkeypatch):
    clone = _clone_behind_origin(tmp_path)
    _register_local(clone)
    started = {}
    monkeypatch.setattr(
        InstallJob, "start_install",
        classmethod(lambda cls, **kw: started.update(kw) or
                    {"install_id": "install_2026_01_01_001", "install_state": "checking"}),
    )

    resp = _apply(client)

    assert resp.status_code == 200, resp.get_json()
    assert started["source_type"] == "repo_url", "runs through the repo installer"
    assert started["record_as"] == "local_path", "but stays a local_path record"
    assert started["repo_url"] == Installer.git_remote_url(clone)
    assert started["dest_parent"] == str(clone.parent) and started["repo_name"] == "OG-ETH"


def test_clone_with_local_changes_is_not_updated(client, tmp_path, monkeypatch):
    clone = _clone_behind_origin(tmp_path)
    _register_local(clone)
    (clone / "pyproject.toml").write_text("# edited by hand\n")
    monkeypatch.setattr(InstallJob, "start_install",
                        classmethod(lambda cls, **kw: (_ for _ in ()).throw(AssertionError)))

    body = _check(client)
    assert body["updatable"] is False and "local changes" in body["update_blocked_reason"]
    assert CalibrationRegistry.get("ETH")["updatable"] is False

    resp = _apply(client)
    assert resp.status_code == 400
    assert "local changes" in resp.get_json()["message"]


def test_untracked_files_do_not_block_an_update(client, tmp_path, monkeypatch):
    clone = _clone_behind_origin(tmp_path)
    _register_local(clone)
    (clone / ".venv").mkdir()
    (clone / "scratch.ipynb").write_text("{}")
    monkeypatch.setattr(
        InstallJob, "start_install",
        classmethod(lambda cls, **kw: {"install_id": "install_2026_01_01_001",
                                       "install_state": "checking"}),
    )

    assert _check(client)["updatable"] is True
    assert _apply(client).status_code == 200


def test_detached_clone_is_not_updated(client, tmp_path):
    clone = _clone_behind_origin(tmp_path)
    _register_local(clone)
    _git(["checkout", "-q", "--detach"], clone)

    body = _check(client)
    assert body["updatable"] is False and "track" in body["update_blocked_reason"]

    resp = _apply(client)
    assert resp.status_code == 400
    assert "track" in resp.get_json()["message"]


def test_update_job_keeps_the_local_path_source_type(tmp_path, monkeypatch):
    clone = _clone_behind_origin(tmp_path)
    _register_local(clone)
    monkeypatch.setattr(
        Installer, "run_installer",
        classmethod(lambda cls, **kw: {
            "ok": True, "local_path": str(clone), "venv_path": str(clone / ".venv"),
            "python_path": str(clone / ".venv/bin/python"), "package_name": "ogeth",
            "repo_url": Installer.git_remote_url(clone), "commit_sha": "new",
        }),
    )

    job = InstallJob.start_install(
        source_type="repo_url", country_id="ETH", country_name="Ethiopia",
        repo_name="OG-ETH", dest_parent=str(tmp_path), repo_url="x",
        record_as="local_path",
    )
    assert job is not None
    end = time.time() + 10
    while InstallJob.is_country_active("ETH") and time.time() < end:
        time.sleep(0.02)

    record = CalibrationRegistry.get("ETH")
    assert record["install_state"] == "installed"
    assert record["source_type"] == "local_path", "next update is safety-checked again"
    assert record["commit_sha"] == "new" and record.get("last_updated_at")
