#import ujson as json
import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class File:
    """
    Utility class for safe and consistent file I/O operations.
    Provides JSON read/write helpers with proper error propagation
    and improved reliability.
    """

    @staticmethod
    def _validate_path(path: str) -> Path:
        """Validate and return a Path object. Ensures parent directory exists."""
        p = Path(path)

        if not p.parent.exists():
            raise FileNotFoundError(f"Directory does not exist: {p.parent}")

        return p

    @staticmethod
    def readFile(path: str) -> Dict[str, Any]:
        """
        Read JSON file and return parsed data.
        Raises standard exceptions (FileNotFoundError, PermissionError, JSONDecodeError).
        """
        p = File._validate_path(path)

        logger.debug(f"Reading file from: {p}")

        with p.open(mode="r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def writeFile(data: Dict[str, Any], path: str) -> None:
        """
        Write data to file in formatted JSON using atomic write.
        """
        p = File._validate_path(path)
        temp_path = p.with_suffix(p.suffix + ".tmp")

        logger.debug(f"Writing formatted JSON to: {p} (atomic)")

        with temp_path.open(mode="w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=True, indent=4, sort_keys=False)

        temp_path.replace(p)

    @staticmethod
    def writeFileUJson(data: Dict[str, Any], path: str) -> None:
        """
        Write data to file in compact JSON format using atomic write.
        """
        p = File._validate_path(path)
        temp_path = p.with_suffix(p.suffix + ".tmp")

        logger.debug(f"Writing compact JSON to: {p} (atomic)")

        with temp_path.open(mode="w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))

        temp_path.replace(p)

    @staticmethod
    def readParamFile(path: str) -> Dict[str, Any]:
        """
        Read parameter JSON file.
        Alias for readFile for semantic clarity.
        """
        return File.readFile(path)