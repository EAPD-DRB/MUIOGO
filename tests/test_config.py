"""
Tests for Config.py.

No server needed here -- just import Config and check the paths it sets up
are pointing at the right places.
"""

from pathlib import Path

from Classes.Base import Config


def test_data_storage_is_path_instance():
    assert isinstance(Config.DATA_STORAGE, Path)


def test_webapp_path_is_path_instance():
    assert isinstance(Config.WEBAPP_PATH, Path)


def test_solvers_folder_is_path_instance():
    assert isinstance(Config.SOLVERs_FOLDER, Path)


def test_data_storage_exists():
    # Config creates this folder on import, so it should always be there.
    assert Config.DATA_STORAGE.exists()
    assert Config.DATA_STORAGE.is_dir()


def test_allowed_extensions_contains_zip():
    assert "zip" in Config.ALLOWED_EXTENSIONS


def test_allowed_extensions_xls_contains_xlsx():
    assert "xlsx" in Config.ALLOWED_EXTENSIONS_XLS


def test_heroku_deploy_defaults_to_off():
    # Should be 0 out of the box -- local mode unless explicitly overridden.
    assert Config.HEROKU_DEPLOY == 0


def test_aws_sync_defaults_to_off():
    assert Config.AWS_SYNC == 0


def test_data_storage_is_inside_webapp():
    # DataStorage lives inside WebAPP -- if this is wrong the whole path layout is broken.
    assert Config.WEBAPP_PATH in Config.DATA_STORAGE.parents
