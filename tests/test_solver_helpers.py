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
