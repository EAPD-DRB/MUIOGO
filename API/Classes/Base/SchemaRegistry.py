"""
API/Classes/Base/SchemaRegistry.py  [v2 — Iterator-Aware]
==========================================================
MUIOGO – JSON Schema-Driven Parameter Registry
------------------------------------------------
Replaces DEFAULT_F / UPDATE_F / GEN_F dictionaries in Config.py with a
runtime-generated, validated registry built from Parameters.json.

v2 adds iterator-aware dispatch: BoundRegistry now routes `default_*`
and `update_*` calls through ParameterIterator automatically when no
legacy method exists, eliminating the need for ANY per-group handler
method on CaseClass / UpdateCaseClass.

Migration Path
--------------
Phase 1 (today)   – Registry replaces Config.py dicts. Existing per-group
                    methods (default_RYT, default_RYTM…) still work via
                    legacy dispatch. Missing methods log INFO (not WARNING)
                    because the iterator covers them automatically.
Phase 2 (next PR) – Delete all default_*/update_* methods from CaseClass /
                    UpdateCaseClass. BoundRegistry auto-routes everything
                    through ParameterIterator. Zero new code per new group.
Phase 3 (future)  – Extend ParameterIterator to cover gen_* (solver file
                    formatting). Last remaining per-group boilerplate gone.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency – jsonschema
# ---------------------------------------------------------------------------
try:
    import jsonschema  # type: ignore
    _JSONSCHEMA_AVAILABLE = True
except ImportError:
    _JSONSCHEMA_AVAILABLE = False
    logger.warning(
        "SchemaRegistry: 'jsonschema' not installed. "
        "Parameters.json will be loaded but NOT validated. "
        "Run `pip install jsonschema` to enable validation."
    )

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
GroupKey    = str
MethodName  = str
MappingDict = Dict[GroupKey, MethodName]


# ---------------------------------------------------------------------------
# SchemaRegistry  (singleton)
# ---------------------------------------------------------------------------
class SchemaRegistry:
    """
    Singleton.  Loads Parameters.json once, validates it, generates
    DEFAULT_F / UPDATE_F / GEN_F mappings dynamically from group keys.
    """

    _instance: Optional["SchemaRegistry"] = None
    _lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------
    @classmethod
    def instance(
        cls,
        parameters_path: Optional[Path] = None,
        schema_path:     Optional[Path] = None,
    ) -> "SchemaRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls._create(parameters_path, schema_path)
        return cls._instance

    @classmethod
    def _create(cls, parameters_path, schema_path) -> "SchemaRegistry":
        inst = object.__new__(cls)
        inst._initialise(parameters_path, schema_path)
        return inst

    def __init__(self) -> None:  # pragma: no cover
        raise RuntimeError("Use SchemaRegistry.instance().")

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def _initialise(self, parameters_path, schema_path) -> None:
        base = Path(__file__).parent
        self._parameters_path: Path = (
            parameters_path
            or (base / ".." / ".." / "Data" / "Parameters.json").resolve()
        )
        self._schema_path: Path = (
            schema_path
            or (base / "parameters_schema.json").resolve()
        )

        logger.info("SchemaRegistry: loading '%s'", self._parameters_path)
        raw = self._load_json(self._parameters_path)
        self._validate(raw)

        self._raw: Dict[GroupKey, List[Dict[str, Any]]] = raw
        self._groups: FrozenSet[GroupKey] = frozenset(raw.keys())

        self._default_f: MappingDict = {}
        self._update_f:  MappingDict = {}
        self._gen_f:     MappingDict = {}
        self._build_mappings()

        logger.info(
            "SchemaRegistry: ready  groups=%d  DEFAULT_F=%d  UPDATE_F=%d  GEN_F=%d",
            len(self._groups), len(self._default_f),
            len(self._update_f), len(self._gen_f),
        )

    @staticmethod
    def _load_json(path: Path) -> Dict:
        if not path.exists():
            raise FileNotFoundError(f"SchemaRegistry: not found at '{path}'")
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    def _validate(self, data: Dict) -> None:
        if not _JSONSCHEMA_AVAILABLE:
            logger.warning("SchemaRegistry: skipping validation (jsonschema absent).")
            return
        if not self._schema_path.exists():
            logger.warning("SchemaRegistry: schema file absent, skipping validation.")
            return
        schema = self._load_json(self._schema_path)
        try:
            jsonschema.validate(instance=data, schema=schema)
            logger.info("SchemaRegistry: Parameters.json is valid.")
        except jsonschema.ValidationError as exc:
            path_str = " -> ".join(str(p) for p in exc.absolute_path) or "<root>"
            raise ValueError(
                f"SchemaRegistry: Parameters.json invalid.\n"
                f"  Field: {path_str}\n  Problem: {exc.message}"
            ) from exc

    def _build_mappings(self) -> None:
        for group_key in self._groups:
            for prefix, mapping in (
                ("default", self._default_f),
                ("update",  self._update_f),
                ("gen",     self._gen_f),
            ):
                mapping[group_key] = f"{prefix}_{group_key}"

    # ------------------------------------------------------------------
    # Class binding
    # ------------------------------------------------------------------
    def bind_to_class(self, target_class: type) -> "BoundRegistry":
        """
        Validate handlers against target_class and return a BoundRegistry.
        Groups with no legacy default/update handler are automatically routed
        to ParameterIterator.  Missing gen handlers log a WARNING.
        """
        return BoundRegistry(self, target_class)

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------
    @property
    def DEFAULT_F(self) -> MappingDict:
        return dict(self._default_f)

    @property
    def UPDATE_F(self) -> MappingDict:
        return dict(self._update_f)

    @property
    def GEN_F(self) -> MappingDict:
        return dict(self._gen_f)

    @property
    def groups(self) -> FrozenSet[GroupKey]:
        return self._groups

    def params_for(self, group_key: GroupKey) -> List[Dict[str, Any]]:
        try:
            return list(self._raw[group_key])
        except KeyError:
            raise KeyError(
                f"SchemaRegistry: group '{group_key}' not found. "
                f"Available: {sorted(self._groups)}"
            ) from None

    def default_value(self, group_key: GroupKey, param_id: str) -> Any:
        for entry in self._raw.get(group_key, []):
            if entry["id"] == param_id:
                return entry["default"]
        raise KeyError(
            f"SchemaRegistry: param '{param_id}' not found in group '{group_key}'."
        )

    @classmethod
    def _reset(cls) -> None:  # test use only
        with cls._lock:
            cls._instance = None


# ---------------------------------------------------------------------------
# BoundRegistry
# ---------------------------------------------------------------------------
class BoundRegistry:
    """
    Per-class validated view of SchemaRegistry.

    Dispatch priority for default_* and update_*:
      1. Explicit method exists on the class → call it  (legacy compatibility)
      2. No explicit method                  → ParameterIterator handles it
         (zero new code needed for new parameter groups)

    Dispatch for gen_*:
      gen functions write solver-specific file formats and cannot yet be
      fully genericised.  Missing gen_* handlers log a WARNING.
    """

    def __init__(self, registry: SchemaRegistry, target_class: type) -> None:
        self._registry     = registry
        self._target_class = target_class
        self._class_name   = target_class.__name__

        self._default_f: MappingDict = {}
        self._update_f:  MappingDict = {}
        self._gen_f:     MappingDict = {}

        self._iterator_default: FrozenSet[GroupKey] = frozenset()
        self._iterator_update:  FrozenSet[GroupKey] = frozenset()

        self._classify_groups()

    def _classify_groups(self) -> None:
        iter_default: set = set()
        iter_update:  set = set()

        for group_key in self._registry.groups:
            for prefix, mapping, iter_bucket in (
                ("default", self._default_f, iter_default),
                ("update",  self._update_f,  iter_update),
                ("gen",     self._gen_f,     None),
            ):
                method_name = f"{prefix}_{group_key}"
                if hasattr(self._target_class, method_name):
                    mapping[group_key] = method_name
                elif iter_bucket is not None:
                    # default / update: iterator covers it — info, not warning
                    iter_bucket.add(group_key)
                    logger.info(
                        "SchemaRegistry [%s]: no '%s' — ParameterIterator will handle '%s'.",
                        self._class_name, method_name, group_key,
                    )
                else:
                    # gen: no automatic fallback yet
                    logger.warning(
                        "SchemaRegistry [%s]: no '%s' — "
                        "solver file output for group '%s' will be SKIPPED.",
                        self._class_name, method_name, group_key,
                    )

        self._iterator_default = frozenset(iter_default)
        self._iterator_update  = frozenset(iter_update)

    # ------------------------------------------------------------------
    # Dispatch: default
    # ------------------------------------------------------------------
    def dispatch_default(
        self,
        instance:        Any,
        group_key:       GroupKey,
        *,
        gen_data:        Optional[Dict[str, Any]] = None,
        scenarios:       Optional[List[Dict[str, Any]]] = None,
        scenario_id_key: str = "ScenarioId",
        base_scenario:   str = "SC_0",
    ) -> Any:
        """
        Route a 'default' call.

        Legacy path  → calls instance.default_{group_key}() directly.
        Iterator path → calls ParameterIterator.build_default() and returns
                        the data dict (caller writes it to file).

        Keyword arguments (gen_data, scenarios, …) are only consumed on the
        iterator path.  Legacy methods receive no extra arguments because
        they read genData from self internally.
        """
        if group_key in self._default_f:
            return getattr(instance, self._default_f[group_key])()

        if group_key in self._iterator_default:
            return self._iterator_default_call(
                instance, group_key, gen_data, scenarios,
                scenario_id_key, base_scenario,
            )

        raise KeyError(
            f"BoundRegistry [{self._class_name}]: "
            f"no default handler or iterator coverage for '{group_key}'."
        )

    def _iterator_default_call(
        self, instance, group_key, gen_data, scenarios, scenario_id_key, base_scenario
    ) -> Dict[str, Any]:
        # Late import — avoids circular import between Registry and Iterator
        from API.Classes.Base.ParameterIterator import ParameterIterator

        _gd  = gen_data  or getattr(instance, "genData", None)
        _sc  = scenarios or (_gd.get("osy-scenarios") if _gd else None)

        if _gd is None or _sc is None:
            raise RuntimeError(
                f"ParameterIterator needs gen_data + scenarios for '{group_key}' "
                f"but neither were passed nor found on the instance."
            )

        return ParameterIterator.build_default(
            group_key       = group_key,
            parameters      = self._registry.params_for(group_key),
            gen_data        = _gd,
            scenarios       = _sc,
            scenario_id_key = scenario_id_key,
            base_scenario   = base_scenario,
        )

    # ------------------------------------------------------------------
    # Dispatch: update
    # ------------------------------------------------------------------
    def dispatch_update(
        self,
        instance:        Any,
        group_key:       GroupKey,
        *,
        gen_data:        Optional[Dict[str, Any]] = None,
        scenarios:       Optional[List[Dict[str, Any]]] = None,
        existing_data:   Optional[Dict[str, Any]] = None,
        scenario_id_key: str = "ScenarioId",
        base_scenario:   str = "SC_0",
    ) -> Any:
        """
        Route an 'update' call.

        Legacy path  → calls instance.update_{group_key}() directly.
        Iterator path → calls ParameterIterator.build_update() and returns data.
        """
        if group_key in self._update_f:
            return getattr(instance, self._update_f[group_key])()

        if group_key in self._iterator_update:
            return self._iterator_update_call(
                instance, group_key, gen_data, scenarios,
                existing_data, scenario_id_key, base_scenario,
            )

        raise KeyError(
            f"BoundRegistry [{self._class_name}]: "
            f"no update handler or iterator coverage for '{group_key}'."
        )

    def _iterator_update_call(
        self, instance, group_key, gen_data, scenarios,
        existing_data, scenario_id_key, base_scenario,
    ) -> Dict[str, Any]:
        from API.Classes.Base.ParameterIterator import ParameterIterator

        _gd  = gen_data      or getattr(instance, "genData", None)
        _sc  = scenarios     or (_gd.get("osy-scenarios") if _gd else None)
        _ex  = existing_data

        if _gd is None or _sc is None or _ex is None:
            raise RuntimeError(
                f"ParameterIterator.build_update needs gen_data, scenarios, "
                f"and existing_data for '{group_key}'."
            )

        return ParameterIterator.build_update(
            group_key       = group_key,
            parameters      = self._registry.params_for(group_key),
            gen_data        = _gd,
            scenarios       = _sc,
            existing_data   = _ex,
            scenario_id_key = scenario_id_key,
            base_scenario   = base_scenario,
            keys_exists_fn  = getattr(instance, "keys_exists", None),
        )

    # ------------------------------------------------------------------
    # Dispatch: gen
    # ------------------------------------------------------------------
    def dispatch_gen(self, instance: Any, group_key: GroupKey, *args, **kwargs) -> Any:
        """Call instance.gen_{group_key}(). Raises KeyError if missing."""
        if group_key in self._gen_f:
            return getattr(instance, self._gen_f[group_key])(*args, **kwargs)
        raise KeyError(
            f"BoundRegistry [{self._class_name}]: "
            f"no gen handler for '{group_key}'. Solver output will be missing."
        )

    # ------------------------------------------------------------------
    # Public read-only properties
    # ------------------------------------------------------------------
    @property
    def DEFAULT_F(self) -> MappingDict:
        return dict(self._default_f)

    @property
    def UPDATE_F(self) -> MappingDict:
        return dict(self._update_f)

    @property
    def GEN_F(self) -> MappingDict:
        return dict(self._gen_f)

    @property
    def iterator_groups(self) -> Dict[str, FrozenSet[GroupKey]]:
        """Groups being served by ParameterIterator rather than legacy methods."""
        return {
            "default": self._iterator_default,
            "update":  self._iterator_update,
        }

    @property
    def missing_gen_groups(self) -> FrozenSet[GroupKey]:
        """Groups with no gen_* handler — their solver output will be skipped."""
        return self._registry.groups - frozenset(self._gen_f)

    @property
    def missing_groups(self) -> FrozenSet[GroupKey]:
        """Groups with at least one unresolved handler (legacy or iterator)."""
        covered = (
            frozenset(self._default_f) | self._iterator_default |
            frozenset(self._update_f)  | self._iterator_update  |
            frozenset(self._gen_f)
        )
        return self._registry.groups - covered