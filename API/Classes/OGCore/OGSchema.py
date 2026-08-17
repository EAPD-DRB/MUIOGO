"""Parameter-form metadata built from a calibration's own defaults files.

This module projects OG-Core's user-facing parameter metadata (labels, sections,
ranges, default values) into the compact shape the frontend needs to render input
forms. It reads the defaults JSON that ships inside whatever OG version the user
has actually installed, so the form always matches that version; it never imports
the ogcore package. The projection is faithful but lightly normalized: a handful
of display-only heuristics (type/shape) are derived here, and very large default
arrays are dropped from the payload rather than shipped to the browser.

For a country calibration the base OG-Core definitions are overlaid with the
country's own defaults file, with the country's entries winning on any key.
"""

import glob
import json
import os
from pathlib import Path

from Classes.OGCore.CalibrationRegistry import CalibrationRegistry

# Cache of parsed defaults files, keyed by str(path) -> (mtime, data). A defaults
# file is re-read only when its mtime changes, so repeated schema builds do not
# reparse a multi-hundred-KB JSON on every request.
_DEFAULTS_CACHE: dict[str, tuple[float, dict]] = {}

# Total leaf-element count above which a default value is considered too large to
# ship to the browser; such values are dropped and flagged with "large": True.
_LARGE_VALUE_THRESHOLD = 100


def _entry_value(entry):
    """Return the parameter value from either metadata or a bare overlay entry."""
    if not isinstance(entry, dict):
        return entry
    value_list = entry.get("value")
    if isinstance(value_list, list) and value_list:
        first = value_list[0]
        if isinstance(first, dict) and "value" in first:
            return first["value"]
    return None


def _dimensions(value) -> list[int]:
    """Dimensions of the first rectangular path through a nested list."""
    out = []
    current = value
    while isinstance(current, list):
        out.append(len(current))
        current = current[0] if current else None
    return out


def _preview(value, depth=0):
    """Small nested sample used by the parameter page before lazy loading."""
    if not isinstance(value, list):
        return value
    limit = 4 if depth == 0 else 3
    return [_preview(item, depth + 1) for item in value[:limit]]


def _is_column_matrix(value) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(row, list) and len(row) == 1 for row in value)
    )


def _compact_column_matrix(value):
    """Drop an unchanged trailing schedule while preserving its matrix shape."""
    if not _is_column_matrix(value):
        return value
    compact = list(value)
    while len(compact) > 1 and compact[-1] == compact[-2]:
        compact.pop()
    return compact


def _defaults_filename(package_name: str) -> str:
    """Name of the defaults JSON that ships inside ``package_name``.

    The base model uses a plain ``default_parameters.json``; every country package
    prefixes the file with its own package name.
    """
    if package_name == "ogcore":
        return "default_parameters.json"
    return f"{package_name}_default_parameters.json"


def find_defaults_file(rec, package_name: str) -> Path | None:
    """Locate ``package_name``'s defaults JSON for the calibration ``rec``.

    Tries the base-model repo checkout first, then the package as installed inside
    the calibration's own venv site-packages (which is how a country venv exposes
    ogcore's base file). Returns the first path that exists, else None.
    """
    if not isinstance(rec, dict):
        return None
    filename = _defaults_filename(package_name)
    local_path = rec.get("local_path")
    venv_path = rec.get("venv_path")

    # 1. Repo-tree checkout (only the base model is laid out this way on disk).
    if local_path:
        repo_candidate = Path(local_path) / package_name / filename
        if repo_candidate.is_file():
            return repo_candidate

    # 2. Installed inside the calibration's venv site-packages.
    if venv_path:
        if os.name == "nt":
            sp_candidate = (
                Path(venv_path) / "Lib" / "site-packages" / package_name / filename
            )
            if sp_candidate.is_file():
                return sp_candidate
        else:
            pattern = str(
                Path(venv_path) / "lib" / "python*" / "site-packages" / package_name / filename
            )
            for match in sorted(glob.glob(pattern)):
                candidate = Path(match)
                if candidate.is_file():
                    return candidate

    return None


def load_defaults(path) -> dict | None:
    """Parse a defaults JSON, caching by path+mtime. None on any read/parse error."""
    path = Path(path)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    key = str(path)
    cached = _DEFAULTS_CACHE.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    _DEFAULTS_CACHE[key] = (mtime, data)
    return data


def _is_number(x) -> bool:
    """True for a real int/float, excluding bool (a subclass of int)."""
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _leaf_count(v) -> int:
    """Number of scalar leaves in ``v``, descending into nested lists."""
    if isinstance(v, list):
        return sum(_leaf_count(x) for x in v)
    return 1


def project_entry(name: str, entry) -> dict:
    """Project one raw defaults entry into the compact form-metadata shape.

    Always returns a dict with the fixed key set below; a malformed entry yields a
    projection with ``default`` None rather than raising. The extra ``large`` key
    appears only when the default value was dropped for size.
    """
    if not isinstance(entry, dict):
        entry = {}

    # Range from the entry's validators, only when both bounds are real numbers.
    validators = entry.get("validators")
    rng = None
    if isinstance(validators, dict):
        range_raw = validators.get("range")
        if isinstance(range_raw, dict):
            mn = range_raw.get("min")
            mx = range_raw.get("max")
            if _is_number(mn) and _is_number(mx):
                rng = (mn, mx)

    # Display-only type heuristic:
    #   int + year-like range          -> "year"
    #   int otherwise                  -> "count"
    #   float bounded to [0, 1]        -> "rate"
    #   everything else                -> "level"
    datatype = entry.get("type")
    if datatype == "str":
        param_type = "string"
    elif datatype == "int" and rng and 1900 <= rng[0] and rng[1] <= 2101:
        param_type = "year"
    elif datatype == "int":
        param_type = "count"
    elif datatype == "float" and rng and rng[0] >= 0 and rng[1] <= 1:
        param_type = "rate"
    else:
        param_type = "level"

    # Default value at entry["value"][0]["value"], defensively extracted.
    v = _entry_value(entry)
    dimensions = _dimensions(v) if isinstance(v, list) else None
    display_value = _compact_column_matrix(v)

    # Display-only shape heuristic:
    #   scalar (size 1, no dims)       -> "scalar"
    #   number_dims == 2               -> "time_x_industry"
    #   otherwise                      -> "time"
    size = len(v) if isinstance(v, list) else 1
    if size == 1 and not entry.get("number_dims"):
        shape = "scalar"
    elif entry.get("number_dims") == 2:
        shape = "time_x_industry"
    else:
        shape = "time"

    # Large default arrays are dropped so the browser never receives a multi-KB
    # blob it cannot edit as a form field; the flag lets the UI say so.
    projected: dict = {
        "title": entry.get("title") or name,
        "description": entry.get("description") or "",
        "section": entry.get("section_1") or "",
        "subsection": entry.get("section_2") or None,
        "type": param_type,
        "datatype": datatype,
        "shape": shape,
    }
    if isinstance(validators, dict):
        choice = validators.get("choice")
        choices = choice.get("choices") if isinstance(choice, dict) else None
        if isinstance(choices, list) and choices:
            projected["choices"] = choices
    if _leaf_count(display_value) > _LARGE_VALUE_THRESHOLD and not _is_column_matrix(display_value):
        projected["default"] = None
        projected["large"] = True
        projected["preview"] = _preview(display_value)
    else:
        projected["default"] = display_value
    if dimensions:
        projected["dimensions"] = dimensions
    projected["min"] = rng[0] if rng else None
    projected["max"] = rng[1] if rng else None
    return projected


def _project_all(defaults: dict, into: dict) -> None:
    """Project every entry of ``defaults`` (skipping the top-level schema key)
    into ``into``. Used for the base file, whose entries carry full metadata."""
    for name, entry in defaults.items():
        if name == "schema":
            continue
        into[name] = project_entry(name, entry)


# Keys that only appear in OG-Core's full metadata form, never in a bare value.
_METADATA_MARKERS = ("value", "validators", "title", "section_1")


def _is_metadata_entry(entry) -> bool:
    """True when an entry carries full parameter metadata rather than a bare value."""
    return isinstance(entry, dict) and any(k in entry for k in _METADATA_MARKERS)


def _with_default(entry: dict, value) -> dict:
    """Copy of a projected entry carrying ``value`` as its default."""
    out = dict(entry)
    dimensions = _dimensions(value) if isinstance(value, list) else None
    display_value = _compact_column_matrix(value)
    if _leaf_count(display_value) > _LARGE_VALUE_THRESHOLD and not _is_column_matrix(display_value):
        out["default"] = None
        out["large"] = True
        out["preview"] = _preview(display_value)
    else:
        out["default"] = display_value
        out.pop("large", None)
        out.pop("preview", None)
    if dimensions:
        out["dimensions"] = dimensions
    else:
        out.pop("dimensions", None)
    return out


def _overlay_values(defaults: dict, into: dict) -> None:
    """Overlay a country defaults file onto the base projection.

    A country file stores bare values (``"frisch": 0.4``), not metadata objects, so
    projecting it like the base file would replace every title, description and
    range with an empty one. Keep the base metadata and swap in the country's own
    default, which is the value the user actually has.
    """
    for name, value in defaults.items():
        if name == "schema":
            continue
        if _is_metadata_entry(value):
            into[name] = project_entry(name, value)
            continue
        base = into.get(name)
        if base is None:
            # A parameter the base model does not define: no metadata to keep.
            base = project_entry(name, {})
        into[name] = _with_default(base, value)


def build_schema(case) -> tuple[dict | None, str | None]:
    """Build the parameter-form schema for ``case``.

    Returns (schema, None) on success or (None, error_message) when the case's
    calibration is not installed or its parameter definitions cannot be found.
    """
    try:
        country_id = case.gen_data.get("country_id")
    except (OSError, ValueError, KeyError):
        country_id = None

    rec = CalibrationRegistry.get(country_id)
    if rec is None:
        return None, "That country calibration is not installed."

    # Base OG-Core definitions. For a country package this resolves ogcore inside
    # the country's own venv (the repo-tree candidate exists only for the base
    # model checkout); find_defaults_file handles both.
    base_file = find_defaults_file(rec, "ogcore")
    if base_file is None:
        return None, "The calibration's parameter definitions were not found."
    base_defaults = load_defaults(base_file)
    if base_defaults is None:
        return None, "The calibration's parameter definitions were not found."

    schema: dict = {}
    _project_all(base_defaults, schema)

    # Overlay the country's own defaults, if this is a country calibration.
    package_name = rec.get("package_name")
    if package_name and package_name != "ogcore":
        overlay_file = find_defaults_file(rec, package_name)
        if overlay_file is not None:
            overlay_defaults = load_defaults(overlay_file)
            if overlay_defaults:
                _overlay_values(overlay_defaults, schema)

    return schema, None


def get_parameter_default(case, name: str) -> tuple[object | None, str | None]:
    """Load one full calibration default without expanding the whole schema."""
    try:
        country_id = case.gen_data.get("country_id")
    except (OSError, ValueError, KeyError):
        country_id = None

    rec = CalibrationRegistry.get(country_id)
    if rec is None:
        return None, "That country calibration is not installed."

    base_file = find_defaults_file(rec, "ogcore")
    base_defaults = load_defaults(base_file) if base_file is not None else None
    if base_defaults is None:
        return None, "The calibration's parameter definitions were not found."

    found = name in base_defaults
    value = _entry_value(base_defaults.get(name)) if found else None

    package_name = rec.get("package_name")
    if package_name and package_name != "ogcore":
        overlay_file = find_defaults_file(rec, package_name)
        overlay_defaults = load_defaults(overlay_file) if overlay_file is not None else None
        if overlay_defaults and name in overlay_defaults:
            found = True
            entry = overlay_defaults[name]
            value = _entry_value(entry) if _is_metadata_entry(entry) else entry

    if not found:
        return None, "Parameter not found."
    return value, None
