import logging

from Classes.Base.CustomExceptionClass import CustomException

CURRENT_MODEL_VERSION = "5.0"


class ModelVersionError(CustomException):
    def __init__(self, message, case=None, detected_version=None, expected_version=None):
        payload = {
            "status_code": "version_mismatch",
            "case": case,
            "detected_version": detected_version,
            "expected_version": expected_version or CURRENT_MODEL_VERSION,
        }
        CustomException.__init__(self, message, status_code=409, payload=payload)


def get_model_version(genData):
    if not isinstance(genData, dict):
        return None

    version = genData.get("modelVersion")
    if version is None:
        version = genData.get("osy-version")

    if version is None:
        return None

    version = str(version).strip()
    return version or None


def stamp_model_version(genData, version=CURRENT_MODEL_VERSION):
    if genData is None:
        return genData

    version = str(version).strip() or CURRENT_MODEL_VERSION
    genData["modelVersion"] = version
    genData["osy-version"] = version
    return genData


def validate_model_version(genData, case=None):
    detected_version = get_model_version(genData)

    if detected_version == CURRENT_MODEL_VERSION:
        return detected_version

    if case:
        case_label = f"Model <b>{case}</b>"
    else:
        case_label = "Selected model"

    if detected_version is None:
        message = (
            f"{case_label} is missing schema version metadata. "
            f"Open the model configuration page and click <b>Update model</b> "
            f"before generating data or running the solver."
        )
    else:
        message = (
            f"{case_label} uses schema version <b>{detected_version}</b>, but the current backend "
            f"expects <b>{CURRENT_MODEL_VERSION}</b>. Open the model configuration page and click "
            f"<b>Update model</b> before generating data or running the solver."
        )

    logging.warning(
        "Model version mismatch for case '%s': detected=%s expected=%s",
        case,
        detected_version,
        CURRENT_MODEL_VERSION,
    )
    raise ModelVersionError(
        message,
        case=case,
        detected_version=detected_version,
        expected_version=CURRENT_MODEL_VERSION,
    )
