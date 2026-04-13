from pathlib import Path
import shutil
import uuid

from Classes.Base import Config
from Classes.Base.FileClass import File


def _create_case(case_name, case_runs=None):
    case_dir = Path(Config.DATA_STORAGE, case_name)
    (case_dir / "view").mkdir(parents=True)
    (case_dir / "res").mkdir(parents=True)

    File.writeFile({"osy-casename": case_name}, case_dir / "genData.json")
    File.writeFile({"osy-cases": case_runs or []}, case_dir / "view" / "resData.json")

    for run in case_runs or []:
        (case_dir / "res" / run["Case"]).mkdir(parents=True)

    return case_dir


def test_delete_case_run_deletes_requested_case_run(client):
    case_name = f"delete_run_case_{uuid.uuid4().hex}"
    case_dir = _create_case(case_name, case_runs=[{"Case": "run1"}])

    try:
        response = client.post(
            "/deleteCaseRun",
            json={"casename": case_name, "caserunname": "run1", "resultsOnly": False},
        )

        assert response.status_code == 200
        assert response.get_json() == {
            "message": "You have deleted a case run!",
            "status_code": "success",
        }
        assert not (case_dir / "res" / "run1").exists()
        assert File.readFile(case_dir / "view" / "resData.json") == {"osy-cases": []}
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_delete_case_run_blocks_path_traversal_to_sibling_case(client):
    source_case = f"source_case_{uuid.uuid4().hex}"
    victim_case = f"victim_case_{uuid.uuid4().hex}"
    source_dir = _create_case(source_case)
    victim_dir = _create_case(victim_case)

    try:
        response = client.post(
            "/deleteCaseRun",
            json={
                "casename": source_case,
                "caserunname": f"../../{victim_case}",
                "resultsOnly": False,
            },
        )

        assert response.status_code == 400
        assert response.get_json() == {
            "message": "Invalid path.",
            "status_code": "error",
        }
        assert victim_dir.exists()
    finally:
        shutil.rmtree(source_dir, ignore_errors=True)
        shutil.rmtree(victim_dir, ignore_errors=True)


def test_download_file_blocks_path_traversal_to_sibling_case(client):
    source_case = f"download_source_{uuid.uuid4().hex}"
    victim_case = f"download_victim_{uuid.uuid4().hex}"
    source_dir = _create_case(source_case)
    victim_dir = _create_case(victim_case)
    (source_dir / "res" / "csv").mkdir(parents=True, exist_ok=True)

    try:
        with client.session_transaction() as session_data:
            session_data["osycase"] = source_case

        response = client.get(
            "/downloadFile",
            query_string={"file": f"../../../{victim_case}/genData.json"},
        )

        assert response.status_code == 400
        assert response.get_json() == {
            "message": "Invalid path.",
            "status_code": "error",
        }
        assert victim_dir.exists()
    finally:
        shutil.rmtree(source_dir, ignore_errors=True)
        shutil.rmtree(victim_dir, ignore_errors=True)
