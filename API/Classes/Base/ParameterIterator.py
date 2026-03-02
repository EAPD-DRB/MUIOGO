"""
API/Classes/Base/ParameterIterator.py  (extended — PR #144 / Issue #141)
=========================================================================
Added in this revision
-----------------------
build_update gains two optional callbacks that handle filtered groups
(RYTC, RYTE, RYTEM, RYTCM, RTSM, RYTSM, RYTCn) without bespoke methods:

  item_filter(item, param_id) -> bool
      Return False to skip an item from the primary dimension axis entirely.
      e.g. lambda item, pid: bool(item.get(pid))   # skip techs with no mapping
      e.g. lambda item, pid: bool(item.get('EAR')) # RYTEM fixed-key filter

  item_expander(item, param_id) -> list[dict]
      Given a primary-dimension item that passed the filter, return the list
      of extra identity-key dicts to add to each chunk.
      Each returned dict is merged into the chunk alongside the primary item's
      own identity keys.

      Returning [{}] (a list with one empty dict) means "no expansion" —
      the primary item alone defines the chunk identity (standard behaviour).

      Examples
      --------
      # RYTC — expand over tech's commodity list
      lambda item, pid: [{'CommId': c} for c in item[pid]]

      # RYTSM — derive scalar TechId from stg, then expand over modes
      lambda item, pid: [{'TechId': item[pid], 'MoId': m} for m in range(1, mo+1)]

      # RYTEM — fixed EAR key × modes
      lambda item, pid: [{'EmisId': e, 'MoId': m}
                         for e in item['EAR'] for m in range(1, mo+1)]

The lookup path into existing_data is built from ALL keys present in the
final merged chunk (excluding year keys), sorted by lookup_rank so it
matches the OsemosysClass normaliser nesting order exactly.
"""

from __future__ import annotations

import itertools
import logging
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dimension specification table  (unchanged from original)
# ---------------------------------------------------------------------------

class _DimSpec:
    __slots__ = ("gendata_key", "chunk_key", "id_extractor", "is_year", "is_int_range", "lookup_rank")

    def __init__(
        self,
        gendata_key:  str,
        chunk_key:    str,
        id_extractor: Callable[[Any], Any],
        is_year:      bool = False,
        is_int_range: bool = False,
        lookup_rank:  int  = 99,
    ):
        self.gendata_key  = gendata_key
        self.chunk_key    = chunk_key
        self.id_extractor = id_extractor
        self.is_year      = is_year
        self.is_int_range = is_int_range
        self.lookup_rank  = lookup_rank


_DIM_SPECS: Dict[str, _DimSpec] = {
    "R": _DimSpec(
        gendata_key  = "osy-region",
        chunk_key    = "RegionId",
        id_extractor = lambda item: item["RegionId"],
        lookup_rank  = 4,
    ),
    "Y": _DimSpec(
        gendata_key  = "osy-years",
        chunk_key    = "",
        id_extractor = lambda item: item,
        is_year      = True,
        lookup_rank  = 99,
    ),
    "T": _DimSpec(
        gendata_key  = "osy-tech",
        chunk_key    = "TechId",
        id_extractor = lambda item: item["TechId"],
        lookup_rank  = 1,
    ),
    "M": _DimSpec(
        gendata_key  = "osy-mo",
        chunk_key    = "MoId",
        id_extractor = lambda x: x,
        is_int_range = True,
        lookup_rank  = 3,
    ),
    "C": _DimSpec(
        gendata_key  = "osy-comm",
        chunk_key    = "CommId",
        id_extractor = lambda item: item["CommId"],
        lookup_rank  = 2,
    ),
    "S": _DimSpec(
        gendata_key  = "osy-stg",
        chunk_key    = "StgId",
        id_extractor = lambda item: item["StgId"],
        lookup_rank  = 0,
    ),
}

# lookup_rank for expander-injected keys that aren't in _DIM_SPECS
# (e.g. TechId injected by RTSM/RYTSM expander, ConId injected by RYTCn)
_EXTRA_KEY_RANKS: Dict[str, int] = {
    "TechId": 1,
    "CommId": 2,
    "EmisId": 2,
    "MoId":   3,
    "ConId":  5,
}


# ---------------------------------------------------------------------------
# Internal helpers  (unchanged from original)
# ---------------------------------------------------------------------------

def _resolve_axis(char: str, gen_data: Dict[str, Any]) -> List[Any]:
    spec = _DIM_SPECS.get(char)
    if spec is None:
        raise ValueError(
            f"ParameterIterator: unknown dimension character '{char}'. "
            f"Known dimensions: {sorted(_DIM_SPECS.keys())}."
        )
    raw = gen_data.get(spec.gendata_key)
    if raw is None:
        logger.warning(
            "ParameterIterator: dimension '%s' maps to genData key '%s' which is absent.",
            char, spec.gendata_key,
        )
        return []
    if spec.is_int_range:
        try:
            return list(range(1, int(raw) + 1))
        except (TypeError, ValueError):
            raise ValueError(f"ParameterIterator: 'osy-mo' must be integer-like, got {raw!r}")
    return list(raw)


def _non_year_dims(group_key: str) -> str:
    return "".join(c for c in group_key if c != "Y")


def _cartesian_axes(
    group_key: str,
    gen_data:  Dict[str, Any],
) -> Tuple[List[str], List[List[Any]]]:
    chars = list(_non_year_dims(group_key))
    axes  = [_resolve_axis(c, gen_data) for c in chars]
    return chars, axes


def _iter_combinations(
    chars: List[str],
    axes:  List[List[Any]],
) -> Iterator[Dict[str, Any]]:
    if not chars:
        yield {}
        return
    specs = [_DIM_SPECS[c] for c in chars]
    for combo in itertools.product(*axes):
        yield {spec.chunk_key: spec.id_extractor(item) for spec, item in zip(specs, combo)}


def _year_list(gen_data: Dict[str, Any]) -> List[str]:
    return list(gen_data.get("osy-years", []))


def _lookup_path_from_chunk(
    param_id: str,
    sc_id:    str,
    year:     str,
    chunk:    Dict[str, Any],
    years_set: frozenset,
) -> List[Any]:
    """
    Build the normaliser lookup path for a chunk.

    Path structure: [param_id, sc_id, year, <dims sorted by lookup_rank>]

    Dims are all chunk keys except year-keys, sorted by their rank so the
    path matches the OsemosysClass normaliser nesting order.
    """
    identity_keys = {k: v for k, v in chunk.items() if k not in years_set}

    def rank(key: str) -> int:
        # Check _DIM_SPECS chunk_keys first
        for spec in _DIM_SPECS.values():
            if spec.chunk_key == key:
                return spec.lookup_rank
        # Fall back to extra-key rank table
        return _EXTRA_KEY_RANKS.get(key, 99)

    ranked_ids = [v for _, v in sorted(identity_keys.items(), key=lambda kv: rank(kv[0]))]
    return [param_id, sc_id, year] + ranked_ids


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class ParameterIterator:
    """
    Stateless engine.  All methods are static.

    build_default  – new Case (all values = param.default for SC_0, else None)
    build_update   – existing Case, preserving stored values; supports
                     item_filter and item_expander callbacks for filtered groups
    """

    @staticmethod
    def build_default(
        group_key:       str,
        parameters:      List[Dict[str, Any]],
        gen_data:        Dict[str, Any],
        scenarios:       List[Dict[str, Any]],
        scenario_id_key: str = "ScenarioId",
        base_scenario:   str = "SC_0",
    ) -> Dict[str, Any]:
        years  = _year_list(gen_data)
        chars, axes = _cartesian_axes(group_key, gen_data)
        result: Dict[str, Any] = {}

        for param in parameters:
            param_id      = param["id"]
            default_value = param["default"]
            result[param_id] = {}

            for scenario in scenarios:
                sc_id  = scenario[scenario_id_key]
                chunks = []
                for identity in _iter_combinations(chars, axes):
                    chunk = dict(identity)
                    for year in years:
                        chunk[year] = default_value if sc_id == base_scenario else None
                    chunks.append(chunk)
                result[param_id][sc_id] = chunks

        return result

    @staticmethod
    def build_update(
        group_key:        str,
        parameters:       List[Dict[str, Any]],
        gen_data:         Dict[str, Any],
        scenarios:        List[Dict[str, Any]],
        existing_data:    Dict[str, Any],
        scenario_id_key:  str = "ScenarioId",
        base_scenario:    str = "SC_0",
        keys_exists_fn:   Optional[Callable[..., bool]] = None,
        item_filter:      Optional[Callable[[Any, str], bool]] = None,
        item_expander:    Optional[Callable[[Any, str], List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """
        Rebuild chunk list for an existing Case.

        Parameters
        ----------
        item_filter : Callable[[item, param_id], bool] | None
            Called for every item on the *primary* (first non-Y) dimension axis.
            Return False to skip the item entirely for this param.
            When None, all items are included (standard behaviour).

        item_expander : Callable[[item, param_id], list[dict]] | None
            Called for every item that passed item_filter.
            Returns a list of extra identity dicts to merge into each chunk.
            Returning [{}] means no expansion (one chunk per primary item).
            When None, the standard Cartesian product across ALL dims is used.

            When item_expander is provided the group_key is used ONLY to
            identify the primary dimension axis (first non-Y char).  All
            remaining dims are handled by the expander.
        """
        years      = _year_list(gen_data)
        years_set  = frozenset(years)
        _safe_get  = keys_exists_fn or _default_keys_exists

        # When an expander is given, only the primary axis is iterated by the
        # engine; everything else comes from the expander.
        if item_expander is not None:
            primary_chars = [_non_year_dims(group_key)[0]] if _non_year_dims(group_key) else []
            primary_axes  = [_resolve_axis(primary_chars[0], gen_data)] if primary_chars else [[]]
        else:
            primary_chars, primary_axes = _cartesian_axes(group_key, gen_data)

        result: Dict[str, Any] = {}

        for param in parameters:
            param_id      = param["id"]
            default_value = param["default"]
            result[param_id] = {}

            for scenario in scenarios:
                sc_id  = scenario[scenario_id_key]
                chunks: List[Dict[str, Any]] = []

                # Primary axis items (single axis when expander active)
                primary_items = primary_axes[0] if item_expander is not None else None

                if item_expander is not None:
                    # --- Filtered + expanded path ---
                    for item in primary_items:
                        if item_filter and not item_filter(item, param_id):
                            continue

                        # Primary identity (e.g. {"TechId": "TECH_1"})
                        primary_spec    = _DIM_SPECS[primary_chars[0]]
                        primary_id_dict = {primary_spec.chunk_key: primary_spec.id_extractor(item)}

                        for extra in item_expander(item, param_id):
                            chunk = {**primary_id_dict, **extra}

                            for year in years:
                                path = _lookup_path_from_chunk(param_id, sc_id, year, chunk, years_set)
                                if _safe_get(existing_data, *path):
                                    chunk[year] = _nested_get(existing_data, path)
                                elif sc_id == base_scenario:
                                    chunk[year] = default_value
                                else:
                                    chunk[year] = None

                            chunks.append(chunk)

                else:
                    # --- Standard Cartesian path (original behaviour) ---
                    specs = [_DIM_SPECS[c] for c in primary_chars]
                    for identity in _iter_combinations(primary_chars, primary_axes):
                        chunk = dict(identity)

                        for year in years:
                            ranked_specs = sorted(specs, key=lambda s: s.lookup_rank)
                            lookup_path  = [param_id, sc_id, year] + [
                                identity[spec.chunk_key] for spec in ranked_specs
                            ]
                            if _safe_get(existing_data, *lookup_path):
                                chunk[year] = _nested_get(existing_data, lookup_path)
                            elif sc_id == base_scenario:
                                chunk[year] = default_value
                            else:
                                chunk[year] = None

                        chunks.append(chunk)

                result[param_id][sc_id] = chunks

        return result

    @staticmethod
    def describe_group(group_key: str, gen_data: Dict[str, Any]) -> Dict[str, Any]:
        chars, axes = _cartesian_axes(group_key, gen_data)
        combo_count = 1
        for ax in axes:
            combo_count *= max(len(ax), 1)
        return {
            "group_key":    group_key,
            "dimensions":   chars,
            "year_count":   len(_year_list(gen_data)),
            "combinations": combo_count,
            "axes_lengths": {c: len(ax) for c, ax in zip(chars, axes)},
        }

    @staticmethod
    def register_dimension(
        char:         str,
        gendata_key:  str,
        chunk_key:    str,
        id_extractor: Callable[[Any], Any],
        is_int_range: bool = False,
    ) -> None:
        if char in _DIM_SPECS:
            logger.warning("ParameterIterator.register_dimension: overwriting spec for '%s'.", char)
        _DIM_SPECS[char] = _DimSpec(
            gendata_key  = gendata_key,
            chunk_key    = chunk_key,
            id_extractor = id_extractor,
            is_int_range = is_int_range,
        )
        logger.info("ParameterIterator: registered dimension '%s' → '%s'.", char, gendata_key)


# ---------------------------------------------------------------------------
# Private utilities
# ---------------------------------------------------------------------------

def _default_keys_exists(data: Any, *keys: Any) -> bool:
    node = data
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return False
        node = node[key]
    return True


def _nested_get(data: Any, keys: List[Any]) -> Any:
    node = data
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node