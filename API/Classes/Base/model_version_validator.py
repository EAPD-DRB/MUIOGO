# API/Classes/Base/model_version_validator.py

from API.Config.version import CURRENT_MODEL_VERSION


class ModelVersionMismatchError(Exception):
    def __init__(self, detected_version, expected_version):
        self.detected_version = detected_version
        self.expected_version = expected_version
        super().__init__(
            f"Model version mismatch. Detected={detected_version}, Expected={expected_version}"
        )


def validate_model_version(model_dict: dict):
    detected_version = model_dict.get("modelVersion")

    if detected_version is None:
        # Legacy model or missing field
        raise ModelVersionMismatchError(
            detected_version="LEGACY_OR_MISSING",
            expected_version=CURRENT_MODEL_VERSION,
        )

    if detected_version != CURRENT_MODEL_VERSION:
        raise ModelVersionMismatchError(
            detected_version=detected_version,
            expected_version=CURRENT_MODEL_VERSION,
        )

    return True