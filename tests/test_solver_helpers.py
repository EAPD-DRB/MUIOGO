import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
"""
Tests for the matrix-reuse helpers on DataFile.

File-based helpers and mocked runner paths -- no solver binaries or case
data needed.
"""

from Classes.Case.DataFileClass import DataFile
from Classes.Case.OsemosysClass import Osemosys
from Classes.Base import Config


def test_matrix_fingerprint_tracks_inputs_and_flavor(tmp_path):
    m = tmp_path / "model.txt"
    d = tmp_path / "data.txt"
    m.write_text("model v1")
    d.write_text("data v1")
    a = DataFile._matrix_fingerprint(m, d, "exact")
    assert a == DataFile._matrix_fingerprint(m, d, "exact")          # stable
    assert a != DataFile._matrix_fingerprint(m, d, "relaxed")        # flavor matters
    d.write_text("data v2")
    assert a != DataFile._matrix_fingerprint(m, d, "exact")          # data change detected


def test_batch_workers_formula(monkeypatch):
    monkeypatch.delenv("MUIOGO_BATCH_WORKERS", raising=False)
    monkeypatch.setattr(DataFile, "_performance_cores", staticmethod(lambda: 4))
    monkeypatch.setattr(DataFile, "_total_memory_gb", staticmethod(lambda: 24.0))
    assert DataFile._batch_workers(4) == 3          # 4 P-cores, 24 GB (measured optimum)
    assert DataFile._batch_workers(2) == 2          # never more than scenarios
    monkeypatch.setattr(DataFile, "_total_memory_gb", staticmethod(lambda: 8.0))
    assert DataFile._batch_workers(4) == 1          # small laptop: sequential
    monkeypatch.setattr(DataFile, "_total_memory_gb", staticmethod(lambda: 16.0))
    assert DataFile._batch_workers(4) == 2          # 16 GB: two at a time
    monkeypatch.setattr(DataFile, "_performance_cores", staticmethod(lambda: 16))
    monkeypatch.setattr(DataFile, "_total_memory_gb", staticmethod(lambda: 64.0))
    assert DataFile._batch_workers(12) == 12        # big machine: no fixed cap
    assert DataFile._batch_workers(20) == 14        # ...until memory limits it


def test_performance_cores_is_sane():
    cores = DataFile._performance_cores()
    assert isinstance(cores, int) and 1 <= cores <= (os.cpu_count() or 1)


def test_batch_workers_override(monkeypatch):
    monkeypatch.setattr(DataFile, "_performance_cores", staticmethod(lambda: 10))
    monkeypatch.setattr(DataFile, "_total_memory_gb", staticmethod(lambda: 64.0))
    monkeypatch.setenv("MUIOGO_BATCH_WORKERS", "12")
    assert DataFile._batch_workers(12) == 12        # override wins upward
    monkeypatch.setenv("MUIOGO_BATCH_WORKERS", "1")
    assert DataFile._batch_workers(8) == 1          # force sequential
    monkeypatch.setenv("MUIOGO_BATCH_WORKERS", "0")
    assert DataFile._batch_workers(8) == 1          # clamped to 1
    monkeypatch.setenv("MUIOGO_BATCH_WORKERS", "nonsense")
    assert DataFile._batch_workers(8) == 8          # bad value: formula applies


@pytest.fixture
def mocked_runner(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATA_STORAGE", tmp_path)
    monkeypatch.setattr(
        Osemosys, "_find_solver_binary",
        staticmethod(lambda folder, name, **kwargs: folder / name),
    )
    runner = SimpleNamespace(
        case="CASE",
        osemosysFile=tmp_path / "model.txt",
        osemosysFileOriginal=tmp_path / "original.txt",
        glpkFolder=tmp_path / "glpk",
        cbcFolder=tmp_path / "cbc",
        glpsol_is_bundled=False,
        cbc_is_bundled=False,
        preprocessData=Mock(),
        _ensure_lp_matrix=Mock(),
        deleteCaseResultsJSON=Mock(),
        generateCSVfromCBC=Mock(),
        generateResultsViewer=Mock(),
    )
    cbc = Mock(return_value=subprocess.CompletedProcess(
        args=["cbc"], returncode=0,
        stdout="Optimal - objective value 1\nTotal time (CPU seconds): 0.00\n", stderr="",
    ))
    monkeypatch.setattr("Classes.Case.DataFileClass.subprocess.run", cbc)
    run_dir = tmp_path / "CASE" / "res" / "REF"
    run_dir.mkdir(parents=True)
    (run_dir / "results.txt").write_text("previous results")
    return runner, cbc, run_dir


@pytest.mark.parametrize("returncode,old_lp", [(1, False), (1, True), (0, False)])
def test_cbc_is_not_started_without_a_successful_matrix(mocked_runner, returncode, old_lp):
    runner, cbc, run_dir = mocked_runner
    if old_lp:
        (run_dir / "lp.lp").write_text("previous matrix")
    runner._ensure_lp_matrix.return_value = (
        subprocess.CompletedProcess(["glpsol"], returncode, "matrix check output", "diagnostic"),
        False,
    )
    lock = Mock()

    result = DataFile.run(runner, "cbc", "REF", lock, postprocess=False)

    assert result["status_code"] == "error"
    assert result["cbc_message"] == ""
    assert result["glpk_message"] == "matrix check output"
    assert result["glpk_stdmsg"] == "diagnostic"
    assert "CBC was not started" in result["timer"]
    cbc.assert_not_called()
    runner.generateCSVfromCBC.assert_not_called()
    assert (run_dir / "results.txt").read_text() == "previous results"
    lock.acquire.assert_called_once()
    lock.release.assert_called_once()


@pytest.mark.parametrize("reused", [False, True])
def test_successful_matrix_still_reaches_cbc(mocked_runner, reused):
    runner, cbc, run_dir = mocked_runner
    (run_dir / "lp.lp").write_text("valid matrix")
    runner._ensure_lp_matrix.return_value = (
        subprocess.CompletedProcess(["glpsol"], 0, "matrix available", ""), reused,
    )
    lock = Mock()

    result = DataFile.run(runner, "cbc", "REF", lock, postprocess=False)

    assert result["status_code"] == "success"
    cbc.assert_called_once()
    assert Path(cbc.call_args.args[0][1]) == (run_dir / "lp.lp").resolve()
    lock.release.assert_called_once()


def test_preprocessing_failure_releases_run_lock(mocked_runner):
    runner, cbc, _ = mocked_runner
    runner.preprocessData.side_effect = ValueError("invalid source data")
    lock = Mock()

    with pytest.raises(ValueError, match="invalid source data"):
        DataFile.run(runner, "cbc", "REF", lock, postprocess=False)

    cbc.assert_not_called()
    lock.release.assert_called_once()
