import pytest

from API.Classes.Base.model_version_validator import (
    validate_model_version,
    ModelVersionMismatchError,
)
from API.Config.version import CURRENT_MODEL_VERSION


def test_valid_version_passes():
    model = {"modelVersion": CURRENT_MODEL_VERSION}
    assert validate_model_version(model) is True


def test_missing_version_raises():
    model = {}
    with pytest.raises(ModelVersionMismatchError):
        validate_model_version(model)


def test_mismatched_version_raises():
    model = {"modelVersion": "1.0"}
    with pytest.raises(ModelVersionMismatchError):
        validate_model_version(model)