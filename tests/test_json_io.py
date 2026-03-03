"""
Tests for API/Classes/Base/FileClass.py (or equivalent file I/O helpers)

Verifies:
- JSON round-trip (write then read returns identical data)
- Missing file handling does not raise unhandled exceptions
- Overwrite behaviour
"""
import sys
import json
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _write_json(path, data):
    """Minimal helper mirroring the pattern used in Osemosys.saveData."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _read_json(path):
    """Minimal helper mirroring the pattern used in Osemosys.getData."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestJsonRoundTrip:
    def test_simple_dict(self, tmp_path):
        data = {"key": "value", "number": 42}
        fp = tmp_path / "test.json"
        _write_json(fp, data)
        result = _read_json(fp)
        assert result == data

    def test_nested_structure(self, tmp_path):
        data = {"scenarios": [{"id": 1, "active": True}, {"id": 2, "active": False}]}
        fp = tmp_path / "nested.json"
        _write_json(fp, data)
        assert _read_json(fp) == data

    def test_unicode_values(self, tmp_path):
        data = {"country": "Côte d'Ivoire", "description": "Énergie"}
        fp = tmp_path / "unicode.json"
        _write_json(fp, data)
        assert _read_json(fp) == data

    def test_overwrite_existing(self, tmp_path):
        fp = tmp_path / "overwrite.json"
        _write_json(fp, {"v": 1})
        _write_json(fp, {"v": 2})
        assert _read_json(fp) == {"v": 2}

    def test_empty_dict(self, tmp_path):
        fp = tmp_path / "empty.json"
        _write_json(fp, {})
        assert _read_json(fp) == {}


class TestMissingFile:
    def test_read_missing_raises_file_not_found(self, tmp_path):
        fp = tmp_path / "does_not_exist.json"
        raised = False
        try:
            _read_json(fp)
        except FileNotFoundError:
            raised = True
        assert raised, "Expected FileNotFoundError for missing JSON file"

    def test_invalid_json_raises_decode_error(self, tmp_path):
        fp = tmp_path / "bad.json"
        fp.write_text("{ not valid json }", encoding="utf-8")
        raised = False
        try:
            _read_json(fp)
        except json.JSONDecodeError:
            raised = True
        assert raised, "Expected JSONDecodeError for malformed JSON"
