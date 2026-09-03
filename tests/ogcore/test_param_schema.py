"""Parameter-form schema, base and country.

A country defaults file stores bare values rather than metadata objects, so the
overlay has to carry the country's default onto the base metadata instead of
replacing the entry. Otherwise every country parameter loses its title,
description and range.
"""
import json

import pytest

from Classes.OGCore import OGSchema

BASE_DEFAULTS = {
    "schema": {"labels": {}},
    "frisch": {
        "title": "Frisch elasticity of labor supply",
        "description": "How responsive labour supply is.",
        "section_1": "Household",
        "type": "float",
        "validators": {"range": {"min": 0.2, "max": 0.62}},
        "value": [{"value": 0.4}],
    },
    "cit_rate": {
        "title": "Corporate income tax rate",
        "description": "Tax on corporate income.",
        "section_1": "Fiscal",
        "type": "float",
        "validators": {"range": {"min": 0.0, "max": 1.0}},
        "value": [{"value": [[0.21]]}],
        "number_dims": 2,
    },
    "method": {
        "title": "Method",
        "description": "The numerical method.",
        "type": "str",
        "validators": {"choice": {"choices": ["first", "second"]}},
        "value": [{"value": "first"}],
    },
}

COUNTRY_DEFAULTS = {
    "frisch": 0.5,
    "cit_rate": [[0.3]],
    "delta_tau_annual": [[0.027]] * 400,
    "e": [[0.1] * 60] * 3,
}


def _write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture
def schema_files(tmp_path, monkeypatch):
    """Point the schema builder at a synthetic base file and country overlay."""
    base = _write(tmp_path, "default_parameters.json", BASE_DEFAULTS)
    country = _write(tmp_path, "ogxyz_default_parameters.json", COUNTRY_DEFAULTS)

    def fake_find(rec, package_name):
        return base if package_name == "ogcore" else country

    monkeypatch.setattr(OGSchema, "find_defaults_file", fake_find)
    return base, country


class _Case:
    """Minimal stand-in for OGCoreCase: build_schema only reads gen_data."""

    def __init__(self, country_id):
        self.gen_data = {"country_id": country_id}


def _build(monkeypatch, package_name):
    monkeypatch.setattr(
        OGSchema.CalibrationRegistry, "get",
        staticmethod(lambda cid: {"package_name": package_name, "local_path": "/x"}),
    )
    schema, err = OGSchema.build_schema(_Case("XYZ"))
    assert err is None
    return schema


def test_base_schema_has_full_metadata(schema_files, monkeypatch):
    schema = _build(monkeypatch, "ogcore")
    assert schema["frisch"]["title"] == "Frisch elasticity of labor supply"
    assert schema["frisch"]["default"] == 0.4
    assert (schema["frisch"]["min"], schema["frisch"]["max"]) == (0.2, 0.62)
    assert schema["method"]["datatype"] == "str"
    assert schema["method"]["type"] == "string"
    assert schema["method"]["choices"] == ["first", "second"]


def test_country_overlay_keeps_metadata_and_takes_country_default(
    schema_files, monkeypatch
):
    schema = _build(monkeypatch, "ogxyz")
    frisch = schema["frisch"]
    assert frisch["title"] == "Frisch elasticity of labor supply", "title kept"
    assert frisch["description"], "description kept"
    assert (frisch["min"], frisch["max"]) == (0.2, 0.62), "range kept"
    assert frisch["default"] == 0.5, "country value wins"
    assert schema["cit_rate"]["default"] == [[0.3]]
    assert schema["cit_rate"]["shape"] == "time_x_industry", "base shape kept"


def test_country_overlay_strips_no_base_parameter(schema_files, monkeypatch):
    # Every parameter the base model documents must still be documented after the
    # overlay. (A country-only parameter has no base metadata to keep, and a large
    # value is dropped on purpose, so both are out of scope here.)
    schema = _build(monkeypatch, "ogxyz")
    documented = [name for name in BASE_DEFAULTS if name != "schema"]
    stripped = [
        name for name in documented
        if not schema[name].get("description")
        or (schema[name].get("datatype") != "str" and schema[name].get("min") is None)
    ]
    assert stripped == [], "no base parameter loses its metadata to the overlay"


def test_country_large_value_is_dropped_and_flagged(schema_files, monkeypatch):
    # 180 leaves: too big to ship to a form field, so it is dropped but declared.
    schema = _build(monkeypatch, "ogxyz")
    assert schema["e"]["default"] is None and schema["e"]["large"] is True
    assert schema["e"]["dimensions"] == [3, 60]
    assert len(schema["e"]["preview"]) == 3
    assert len(schema["e"]["preview"][0]) == 3


def test_repeated_column_matrix_is_a_compact_schedule(schema_files, monkeypatch):
    schema = _build(monkeypatch, "ogxyz")
    schedule = schema["delta_tau_annual"]
    assert schedule["default"] == [[0.027]]
    assert schedule["dimensions"] == [400, 1]
    assert "large" not in schedule


def test_large_default_can_be_loaded_on_demand(schema_files, monkeypatch):
    monkeypatch.setattr(
        OGSchema.CalibrationRegistry, "get",
        staticmethod(lambda cid: {"package_name": "ogxyz", "local_path": "/x"}),
    )
    value, err = OGSchema.get_parameter_default(_Case("XYZ"), "e")
    assert err is None
    assert value == COUNTRY_DEFAULTS["e"]

    value, err = OGSchema.get_parameter_default(_Case("XYZ"), "missing")
    assert value is None
    assert err == "Parameter not found."


def test_country_only_parameter_is_still_projected(schema_files, monkeypatch, tmp_path):
    # A parameter the base model does not define has no metadata to keep, but must
    # still appear with its value.
    _write(tmp_path, "ogxyz_default_parameters.json", {"local_only": 7})
    OGSchema._DEFAULTS_CACHE.clear()
    schema = _build(monkeypatch, "ogxyz")
    assert schema["local_only"]["default"] == 7
    assert schema["local_only"]["title"] == "local_only"


def test_metadata_shaped_country_file_is_projected_normally(
    schema_files, monkeypatch, tmp_path
):
    # Not how OG-Core ships country files today, but a country package that used the
    # full metadata form must not be mistaken for a bare value.
    _write(tmp_path, "ogxyz_default_parameters.json", {
        "frisch": {"title": "Country frisch", "value": [{"value": 0.7}]},
    })
    OGSchema._DEFAULTS_CACHE.clear()
    schema = _build(monkeypatch, "ogxyz")
    assert schema["frisch"]["title"] == "Country frisch"
    assert schema["frisch"]["default"] == 0.7
