"""Discovering a repository's installable models from its layout (no manifest)."""
import json

import pytest

from Classes.Clews import RepoScan
from Classes.Clews.CountryManifest import CountrySource, ManifestError, validate_manifest


PHL_LISTING = [
    "README.md",
    "Philippines_v12_CLEWs_build/muio/SHA256SUMS",
    "Philippines_v12_CLEWs_build/muio/Philippines_v12_v12.0.0_MUIO.zip",
    "Philippines_v12_CLEWs_build/muio/Philippines_v12_ENV_LAND_v12.0.0_MUIO.zip",
    "Philippines_v12_CLEWs_build/muio/Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC_v12.0.0_MUIO.zip",
    "Philippines_v16_CLEWs_build/muio/SHA256SUMS",
    "Philippines_v16_CLEWs_build/muio/Philippines_v15_v15.0.0_MUIO.zip",   # predecessor copy
    "Philippines_v16_CLEWs_build/muio/Philippines_v16_v16.0.0_MUIO.zip",
    "Philippines_v16_CLEWs_build/notes.md",
    "Philippines_vIS2_CLEWs_build/muio/SHA256SUMS",
    "Philippines_vIS2_CLEWs_build/muio/Philippines_vIS2_vIS2.0.0_MUIO.zip",
    "Philippines_v36_CLEWs_build/muio/SHA256SUMS",
    "Philippines_v36_CLEWs_build/muio/Philippines_v36_v36.0.0_MUIO.zip",
    "Philippines_v9_CLEWs_build/README.md",                                 # no sums, no zips
]


def test_versions_come_from_folders_with_checksums_and_archives():
    m = manifest = RepoScan.manifest_from_listing(PHL_LISTING, None, repo_name="CLEWs-PHL")
    validate_manifest(manifest)
    assert m["discovered"] is True
    assert m["iso3"] == "PHL"          # from the repository name CLEWs-PHL
    assert m["name"] == "Philippines"  # the prefix every folder shares
    assert [v["id"] for v in m["vintages"]] == ["vIS2", "v36", "v16", "v12"]  # by name, newest-looking first
    assert m["ordering"] == "name"
    assert not any(v.get("recommended") for v in m["vintages"])


def test_only_the_folders_own_archives_count():
    m = RepoScan.manifest_from_listing(PHL_LISTING, None, repo_name="CLEWs-PHL")
    v16 = next(v for v in m["vintages"] if v["id"] == "v16")
    assert [c["archive"] for c in v16["cases"]] == ["Philippines_v16_v16.0.0_MUIO.zip"]
    assert v16["cases"][0]["case"] == "Philippines_v16"
    assert v16["cases"][0]["recommended"] is True


def test_case_names_and_the_plain_case_is_the_default():
    m = RepoScan.manifest_from_listing(PHL_LISTING, None, repo_name="CLEWs-PHL")
    v12 = next(v for v in m["vintages"] if v["id"] == "v12")
    names = {c["case"]: c for c in v12["cases"]}
    assert set(names) == {"Philippines_v12", "Philippines_v12_ENV_LAND",
                          "Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC"}
    assert names["Philippines_v12"]["recommended"] is True
    assert "recommended" not in names["Philippines_v12_ENV_LAND"]


def test_dates_order_versions_and_win_over_names():
    dates = {
        "Philippines_v12_CLEWs_build/muio": "2026-01-01T00:00:00Z",
        "Philippines_v16_CLEWs_build/muio": "2026-03-01T00:00:00Z",
        "Philippines_v36_CLEWs_build/muio": "2026-08-01T00:00:00Z",
        "Philippines_vIS2_CLEWs_build/muio": "2026-09-01T00:00:00Z",
    }
    m = RepoScan.manifest_from_listing(PHL_LISTING, dates, repo_name="CLEWs-PHL")
    assert m["ordering"] == "date"
    assert [v["id"] for v in m["vintages"]] == ["vIS2", "v36", "v16", "v12"]
    assert m["vintages"][0]["last_changed"] == "2026-09-01T00:00:00Z"
    # a missing date for any folder means the dates cannot be trusted for ordering
    partial = dict(dates)
    del partial["Philippines_v16_CLEWs_build/muio"]
    assert RepoScan.manifest_from_listing(PHL_LISTING, partial, repo_name="CLEWs-PHL")["ordering"] == "name"


def test_fiji_layout_patch_releases_collapse_to_the_highest():
    listing = [
        "Fiji_CLEWs_Global/muio/SHA256SUMS",
        "Fiji_CLEWs_Global/muio/Fiji_CLEWs_Global_raw-v1.0.0_MUIO.zip",
        "Fiji_v2.9_CLEWs_build/muio/SHA256SUMS",
        "Fiji_v2.9_CLEWs_build/muio/Fiji_v2.9_v2.9.0_MUIO.zip",
        "Fiji_v2_CLEWs_calibration/muio/SHA256SUMS",
        "Fiji_v2_CLEWs_calibration/muio/Fiji_v2_v2.0.0_MUIO.zip",
        "Fiji_v2_CLEWs_calibration/muio/Fiji_v2_v2.0.3_MUIO.zip",
        "Fiji_v2_CLEWs_calibration/muio/Fiji_v2_v2.0.1_MUIO.zip",
    ]
    m = RepoScan.manifest_from_listing(listing, None, repo_name="CLEWs-FJI")
    validate_manifest(m)
    assert m["iso3"] == "FJI"
    by_id = {v["id"]: v for v in m["vintages"]}
    assert set(by_id) == {"v2.9", "v2", "Fiji"}      # Fiji_CLEWs_Global has no version token
    assert [c["archive"] for c in by_id["v2"]["cases"]] == ["Fiji_v2_v2.0.3_MUIO.zip"]
    assert by_id["v2"]["cases"][0]["case"] == "Fiji_v2"
    assert by_id["Fiji"]["cases"][0]["case"] == "Fiji_CLEWs_Global"
    # name ordering: v2.9 is newer than v2
    assert m["vintages"].index(by_id["v2.9"]) < m["vintages"].index(by_id["v2"])


def test_register_hints_win_over_derived_country_and_code():
    m = RepoScan.manifest_from_listing(PHL_LISTING, None, repo_name="CLEWs-PHL",
                                       iso3="PHL", name="Philippines (register)")
    assert m["name"] == "Philippines (register)"


def test_nothing_installable_is_a_clean_error():
    with pytest.raises(ManifestError, match="No installable models"):
        RepoScan.manifest_from_listing(["README.md", "docs/guide.pdf"], None, repo_name="Empty")


def test_local_folder_without_manifest_is_scanned(tmp_path):
    v1 = tmp_path / "Testland_v1_CLEWs_build" / "muio"
    v2 = tmp_path / "Testland_v2_CLEWs_build" / "muio"
    for d in (v1, v2):
        d.mkdir(parents=True)
        (d / "SHA256SUMS").write_text("")
    (v1 / "Testland_v1_v1.0.0_MUIO.zip").write_bytes(b"zip")
    (v2 / "Testland_v2_v2.0.0_MUIO.zip").write_bytes(b"zip")
    (v2 / "Testland_v1_v1.0.0_MUIO.zip").write_bytes(b"zip")   # predecessor copy

    source = CountrySource(source_type="local_path", local_path=str(tmp_path))
    m = source.load_manifest()
    assert m["discovered"] is True
    assert m["name"] == "Testland"
    assert [v["id"] for v in m["vintages"]] == ["v2", "v1"]
    assert [c["case"] for c in m["vintages"][0]["cases"]] == ["Testland_v2"]


def test_a_manifest_still_wins_when_present(tmp_path):
    (tmp_path / "x" / "muio").mkdir(parents=True)
    (tmp_path / "x" / "muio" / "SHA256SUMS").write_text("")
    (tmp_path / "x" / "muio" / "Other.zip").write_bytes(b"zip")
    (tmp_path / "clews-country.json").write_text(json.dumps({
        "schema_version": 1, "iso3": "TST", "name": "Declared",
        "vintages": [{"id": "d1", "dir": "x/muio", "cases": [{"case": "Declared", "archive": "Other.zip"}]}],
    }))
    m = CountrySource(source_type="local_path", local_path=str(tmp_path)).load_manifest()
    assert m["name"] == "Declared"
    assert "discovered" not in m


def test_remote_scan_reads_a_git_repository_without_network(tmp_path, clews_state):
    """A blobless clone of a local repository stands in for GitHub: the listing
    and the per-folder dates come from git, newest version first."""
    import os
    import subprocess

    def git(*args, cwd):
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)

    origin = tmp_path / "origin"
    origin.mkdir()
    git("init", "-q", "-b", "main", cwd=origin)
    git("config", "user.email", "t@example.org", cwd=origin)
    git("config", "user.name", "t", cwd=origin)
    stamps = {"v1": "2026-01-01T00:00:00", "v3": "2026-03-01T00:00:00", "v2": "2026-02-01T00:00:00"}
    for v, stamp in stamps.items():   # committed out of version order on purpose
        d = origin / f"Testland_{v}_CLEWs_build" / "muio"
        d.mkdir(parents=True)
        (d / "SHA256SUMS").write_text("")
        (d / f"Testland_{v}_{v}.0.0_MUIO.zip").write_bytes(b"zip")
        git("add", ".", cwd=origin)
        subprocess.run(["git", "commit", "-q", "-m", v], cwd=origin, check=True, capture_output=True,
                       env={**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp})

    m = RepoScan.scan_remote("Local", "Testland", "main", clone_url=str(origin))
    assert m["discovered"] is True and m["ordering"] == "date"
    assert [v["id"] for v in m["vintages"]] == ["v3", "v2", "v1"]
    assert m["vintages"][0]["last_changed"].startswith("2026-03-01")
    # the mirror is kept under the CLEWs state dir and the result is cached
    assert (clews_state / "scan-cache" / "Local__Testland.git" / "HEAD").exists()
    assert RepoScan._cache_read("Local/Testland@main")["vintages"][0]["id"] == "v3"


def test_inspect_route_reports_a_detected_menu(client, tmp_path):
    v = tmp_path / "Testland_v3_CLEWs_build" / "muio"
    v.mkdir(parents=True)
    (v / "SHA256SUMS").write_text("")
    (v / "Testland_v3_v3.0.0_MUIO.zip").write_bytes(b"zip")
    resp = client.post("/clews/inspectSource",
                       json={"source_type": "local_path", "local_path": str(tmp_path)})
    body = resp.get_json()
    assert resp.status_code == 200, body
    assert body["discovered"] is True
    assert body["ordering"] in ("date", "name")
    assert [v["id"] for v in body["vintages"]] == ["v3"]
    assert body["vintages"][0]["cases"][0]["case"] == "Testland_v3"
