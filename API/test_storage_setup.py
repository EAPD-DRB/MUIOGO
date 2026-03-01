"""
Tests for storage_setup.setup_data_directory().

Covers:
  - Happy path: directory created + writable
  - mkdir failure (OSError) re-raised
  - chmod failure (logged warning, not fatal)
  - Unwritable existing directory (PermissionError raised)
"""

import logging
import os
import platform
from pathlib import Path
from unittest import mock

import pytest

from Classes.Base.storage_setup import setup_data_directory


# ── Happy-path tests ──────────────────────────────────────────────────


def test_creates_missing_directory(tmp_path: Path) -> None:
    """Directory is created when it does not exist."""
    target = tmp_path / "new" / "nested" / "DataStorage"
    setup_data_directory(target)
    assert target.is_dir()


def test_existing_directory_is_noop(tmp_path: Path) -> None:
    """No error when the directory already exists."""
    target = tmp_path / "DataStorage"
    target.mkdir()
    setup_data_directory(target)  # should not raise
    assert target.is_dir()


def test_unix_permissions_set(tmp_path: Path) -> None:
    """On Linux/macOS, permissions are set to 0o755."""
    if platform.system() == "Windows":
        pytest.skip("chmod semantics differ on Windows")
    target = tmp_path / "DataStorage"
    setup_data_directory(target)
    assert oct(target.stat().st_mode)[-3:] == "755"


def test_windows_skips_chmod(tmp_path: Path) -> None:
    """On Windows, chmod is skipped entirely."""
    target = tmp_path / "DataStorage"
    with mock.patch("Classes.Base.storage_setup.platform") as mock_plat:
        mock_plat.system.return_value = "Windows"
        setup_data_directory(target)
    assert target.is_dir()


# ── Failure-path tests ────────────────────────────────────────────────


def test_mkdir_failure_is_raised(tmp_path: Path) -> None:
    """OSError from mkdir is logged and re-raised."""
    target = tmp_path / "DataStorage"
    with mock.patch.object(Path, "mkdir", side_effect=OSError("disk full")):
        with pytest.raises(OSError, match="disk full"):
            setup_data_directory(target)


def test_chmod_failure_logs_warning(tmp_path: Path, caplog) -> None:
    """chmod failure logs a warning but does NOT raise."""
    target = tmp_path / "DataStorage"
    target.mkdir()

    with mock.patch("Classes.Base.storage_setup.platform") as mock_plat:
        mock_plat.system.return_value = "Linux"
        with mock.patch.object(
            Path, "chmod", side_effect=OSError("permission denied")
        ):
            with caplog.at_level(logging.WARNING):
                setup_data_directory(target)

    assert "Could not set permissions" in caplog.text


def test_unwritable_directory_raises(tmp_path: Path) -> None:
    """PermissionError is raised when directory is not writable."""
    target = tmp_path / "DataStorage"
    target.mkdir()

    with mock.patch("Classes.Base.storage_setup.os.access", return_value=False):
        with pytest.raises(PermissionError, match="not writable"):
            setup_data_directory(target)
