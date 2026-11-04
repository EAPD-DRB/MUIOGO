"""
DataFile.run() reports its progress and failures through logging (#159).

The app sends the root logger to the console and to the runtime log file, so
anything run() only print()ed never reached the log file. These tests stop
run() before any solver is started, so they need neither GLPK nor CBC.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

API_DIR = str(Path(__file__).resolve().parent.parent / "API")
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from Classes.Case.DataFileClass import DataFile  # noqa: E402


def _datafile_without_solvers(tmp_path):
    datafile = DataFile.__new__(DataFile)
    datafile.case = "LogCase"
    datafile.osemosysFile = tmp_path / "model.txt"
    datafile.osemosysFileOriginal = tmp_path / "model_original.txt"
    datafile._glpkFolder = tmp_path
    datafile._cbcFolder = tmp_path
    datafile._glpsol_is_bundled = False
    datafile._cbc_is_bundled = False
    return datafile


def test_run_failure_is_logged_with_traceback(tmp_path, caplog, capsys):
    datafile = _datafile_without_solvers(tmp_path)

    with patch("Classes.Case.OsemosysClass.Osemosys._find_solver_binary", return_value=None):
        with caplog.at_level(logging.ERROR, logger="Classes.Case.DataFileClass"):
            with pytest.raises(RuntimeError, match="glpsol"):
                datafile.run("glpk", "REF")

    records = [r for r in caplog.records if r.name == "Classes.Case.DataFileClass"]
    assert len(records) == 1
    assert records[0].levelno == logging.ERROR
    assert records[0].getMessage() == "Run REF of model LogCase failed"
    assert records[0].exc_info is not None
    # Nothing is left going straight to stdout
    assert capsys.readouterr().out == ""


def test_run_source_has_no_print_calls():
    import inspect

    assert "print(" not in inspect.getsource(DataFile.run)
