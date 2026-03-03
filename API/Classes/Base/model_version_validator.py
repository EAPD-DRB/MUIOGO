# API/Classes/Base/model_version_validator.py

from API.Classes.Base.version_exceptions import VersionMismatchException
from API.Config.version import CURRENT_MODEL_VERSION
import logging

logger = logging.getLogger(__name__)


def validate_model_version(model_dict):
    """
    Validates that the given model dictionary contains the correct modelVersion.
    """

    detected_version = model_dict.get("modelVersion")

    if detected_version is None:
        logger.warning("Legacy model detected (no modelVersion field)")
        raise VersionMismatchException(
            CURRENT_MODEL_VERSION,
            "LEGACY",
        )

    if detected_version != CURRENT_MODEL_VERSION:
        logger.warning(
            f"Version mismatch detected: expected={CURRENT_MODEL_VERSION}, detected={detected_version}"
        )
        raise VersionMismatchException(
            CURRENT_MODEL_VERSION,
            detected_version,
        )

    return True
    