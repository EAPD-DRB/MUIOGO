"""
Tests for run post-processing: File.writeFile formatting and the pivot
(results-viewer) output.

The pivot test is a golden-output test: it feeds generateResultsViewer a small
stored caserun and asserts the exact emitted structure, so any rewrite of the
pivot loop has to reproduce the old files byte-for-byte (after JSON parsing).
"""

import json

import pytest

from Classes.Base import Config
from Classes.Base.FileClass import File
from Classes.Case.DataFileClass import DataFile


# ---------------------------------------------------------------- writeFile

def test_writefile_default_stays_indented(tmp_path):
    """The default format is multi-line and diffable — the version-controlled
    Parameters/Variables/Duals/Indicators files must not collapse to one line."""
    path = tmp_path / "out.json"
    File.writeFile({"a": 1, "b": [1, 2]}, path)
    text = path.read_text()
    assert len(text.splitlines()) > 1
    assert json.loads(text) == {"a": 1, "b": [1, 2]}


def test_writefile_compact_is_single_line_and_lossless(tmp_path):
    data = {"a": 1, "b": [1, 2], "c": "x"}
    path = tmp_path / "out.json"
    File.writeFile(data, path, indent=None)
    text = path.read_text()
    assert "\n" not in text
    assert json.loads(text) == data


# ------------------------------------------------------------------- pivot

VAR_BY_NAME = {
    "AccumulatedNewCapacity": {"id": "ANC", "group": "RYT", "setrelation": ["r", "t", "y"]},
    "NewCapacity": {"id": "NC", "group": "RYT", "setrelation": ["r", "t", "y"]},
    "ObjectiveValue": {"id": "OV", "group": "R", "setrelation": ["r"]},
}


@pytest.fixture()
def case_on_disk(tmp_path, monkeypatch):
    """A minimal case with one stored caserun, and a DataFile wired to it."""
    monkeypatch.setattr(Config, "DATA_STORAGE", tmp_path)

    csv_dir = tmp_path / "TestCase" / "res" / "RUN1" / "csv"
    csv_dir.mkdir(parents=True)
    view_dir = tmp_path / "TestCase" / "view"
    view_dir.mkdir(parents=True)

    (csv_dir / "AccumulatedNewCapacity.csv").write_text(
        "r,t,y,AccumulatedNewCapacity\n"
        "RE1,COAL,2020,1.5\n"
        "RE1,COAL,2021,2.5\n"
        "RE1,WIND,2020,3.0\n"
        "RE1,WIND,2021,4.0\n"
    )
    (csv_dir / "NewCapacity.csv").write_text(
        "r,t,y,NewCapacity\n"
        "RE1,COAL,2020,0.5\n"
        "RE1,COAL,2021,1.0\n"
    )
    (csv_dir / "ObjectiveValue.csv").write_text(
        "r,ObjectiveValue\n"
        "RE1,-25420.42\n"
    )

    df = DataFile.__new__(DataFile)
    df.case = "TestCase"
    df.viewFolderPath = view_dir
    df.VAR_BY_NAME = VAR_BY_NAME
    df.DUALS_BY_NAME = {}
    df.IND_BY_NAME = {}
    return df, csv_dir, view_dir


def test_pivot_golden_output(case_on_disk):
    df, _, view_dir = case_on_disk
    df.generateResultsViewer("RUN1")

    ryt = json.loads((view_dir / "RYT.json").read_text())
    assert ryt == {
        "ANC": {
            "RUN1": [
                {"Tech": "COAL", "2020": 1.5, "2021": 2.5},
                {"Tech": "WIND", "2020": 3.0, "2021": 4.0},
            ]
        },
        "NC": {
            "RUN1": [
                {"Tech": "COAL", "2020": 0.5, "2021": 1.0},
            ]
        },
    }

    r = json.loads((view_dir / "R.json").read_text())
    assert r == {"OV": {"RUN1": [{"ObjectiveValue": -25420.42}]}}


def test_pivot_merges_into_existing_group_file(case_on_disk):
    """A new run is added beside runs already stored in the group file, and a
    re-run of the same name replaces only its own entry."""
    df, _, view_dir = case_on_disk
    existing = {"ANC": {"OLDRUN": [{"Tech": "COAL", "2020": 9.9}]}}
    (view_dir / "RYT.json").write_text(json.dumps(existing))

    df.generateResultsViewer("RUN1")
    ryt = json.loads((view_dir / "RYT.json").read_text())
    assert ryt["ANC"]["OLDRUN"] == [{"Tech": "COAL", "2020": 9.9}]
    assert ryt["ANC"]["RUN1"][0] == {"Tech": "COAL", "2020": 1.5, "2021": 2.5}

    df.generateResultsViewer("RUN1")  # idempotent re-run
    ryt2 = json.loads((view_dir / "RYT.json").read_text())
    assert ryt2 == ryt


def test_pivot_skips_empty_csv(case_on_disk):
    """A header-only CSV must not create or dirty a group file."""
    df, csv_dir, view_dir = case_on_disk
    for f in csv_dir.iterdir():
        f.unlink()
    (csv_dir / "AccumulatedNewCapacity.csv").write_text("r,t,y,AccumulatedNewCapacity\n")

    df.generateResultsViewer("RUN1")
    assert not (view_dir / "RYT.json").exists()
