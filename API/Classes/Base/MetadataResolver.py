"""
MetadataResolver.py
====================
Singleton adapter for WebAPP/DataStorage/Variables.json.

Replaces the hardcoded VARIABLES_C / DUALS dictionary pattern with a
dynamic, pathlib-based loader that is initialised once per interpreter
session.  All callers receive the same in-memory object after the first
instantiation, keeping I/O cost to a single file read even during batch
runs with hundreds of case runs.
"""

import sys
sys.dont_write_bytecode = True

import json
import threading
from pathlib import Path
from typing import Any

from Classes.Base import Config

class VariableNotFoundError(KeyError):
    """Raised when a variable name is absent from Variables.json."""

class MetadataResolver:
    """
    Singleton resolver for Osemosys variable metadata.

    Thread-safe: the first instantiation parses the JSON under a lock;
    all subsequent instantiations reuse the same populated instance.
    """

    _instance: "MetadataResolver | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "MetadataResolver":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            variables_path: Path = Config.DATA_STORAGE / "Variables.json"
            self._raw: dict[str, list[dict[str, Any]]] = self._load(variables_path)

            self._by_name: dict[str, dict[str, Any]] = {}
            for group, entries in self._raw.items():
                for entry in entries:
                    name = entry.get("name", "")
                    if name:
                        self._by_name[name] = {**entry, "_group": group}

            self._initialized = True

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise FileNotFoundError(
                f"MetadataResolver: Variables.json not found at '{path}'"
            )
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    def get_var_metadata(self, var_name: str) -> dict[str, Any]:
        if var_name not in self._by_name:
            raise VariableNotFoundError(
                f"Variable '{var_name}' not found in Variables.json. "
                f"Known variables: {list(self._by_name.keys())}"
            )

        entry = self._by_name[var_name]

        if var_name in Config.VARIABLES_C:
            dimensions = list(Config.VARIABLES_C[var_name])
        elif var_name in Config.DUALS:
            dimensions = list(Config.DUALS[var_name])
        else:
            dimensions = []

        var_type = "DUAL" if var_name in Config.DUALS else "PRIMAL"

        return {
            "dimensions": dimensions,
            "unit_rule": entry.get("unitRule", {}),
            "type": var_type,
            "group": entry.get("_group", ""),
            "id": entry.get("id", ""),
            "value": entry.get("value", ""),
        }

    def all_variable_names(self) -> list[str]:
        return list(self._by_name.keys())

    def group_for(self, var_name: str) -> str:
        return self.get_var_metadata(var_name)["group"]

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instance = None
