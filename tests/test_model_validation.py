import pytest
import json
from API.Classes.Base.FileClass import File
from API.Classes.Base.version_exceptions import VersionMismatchException
from API.Config.version import CURRENT_MODEL_VERSION

def test_valid_model_load(tmp_path):
    file_path = tmp_path / "valid.json"
    data = {"modelVersion": CURRENT_MODEL_VERSION}
    file_path.write_text(json.dumps(data))

    loaded = File.readFile(file_path)
    assert loaded["modelVersion"] == CURRENT_MODEL_VERSION

def test_mismatched_model_load(tmp_path):
    file_path = tmp_path / "old.json"
    data = {"modelVersion": "0.5"}
    file_path.write_text(json.dumps(data))

    with pytest.raises(VersionMismatchException):
        File.readFile(file_path)

def test_missing_version_load(tmp_path):
    file_path = tmp_path / "legacy.json"
    data = {"name": "legacy"}
    file_path.write_text(json.dumps(data))

    with pytest.raises(VersionMismatchException):
        File.readFile(file_path)
        