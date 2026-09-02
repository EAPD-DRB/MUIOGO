import os
"""
Tests for the matrix-reuse helpers on DataFile.

Pure file-based helpers, tested on tiny synthetic inputs -- no solver
binaries and no case data needed.
"""

from Classes.Case.DataFileClass import DataFile


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
