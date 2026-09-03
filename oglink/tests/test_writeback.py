"""Tests for the OG->CLEWS write-back: the urllib applyPatch client and the CLI
writeback subcommand's dry-run build against the real CLEWs Demo case.
"""
import dataclasses
import io
import json
import os
import urllib.error

import pytest

from oglink import cli, country
from oglink.muiogo_client import apply_via_muiogo


class _FakeResp:
    """Minimal context-manager stand-in for urlopen's return."""

    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._body


def test_apply_via_muiogo_success(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResp({"case_copy": "X", "csv_dir": "/x", "warnings": []})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    patch = {"case": "C", "changes": [{"group": "Demand"}], "deferred": []}
    out = apply_via_muiogo(patch, "REF", base_url="http://127.0.0.1:5000/")
    assert out["case_copy"] == "X"
    assert captured["url"] == "http://127.0.0.1:5000/oglink/applyPatch"
    assert captured["body"] == {"patch": patch, "base_caserun": "REF", "solver": "CBC"}
    # A headless caller sends no Origin -- it must pass the route's cross-site guard.
    assert not any(k.lower() == "origin" for k in captured["headers"])
    assert captured["headers"].get("Content-type") == "application/json"


def test_apply_via_muiogo_http_error_surfaces_blocked(monkeypatch):
    body = json.dumps({"message": "3 of 5 changes cannot be applied; nothing was written.",
                       "blocked": [{"change_index": 2, "reason": "comm code 'ZZZ' is not in this case"}]})
    err = urllib.error.HTTPError("http://x/oglink/applyPatch", 422, "Unprocessable",
                                 {}, io.BytesIO(body.encode("utf-8")))

    def fake_urlopen(req, timeout=None):
        raise err

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(RuntimeError) as ei:
        apply_via_muiogo({"case": "C"}, "REF", base_url="http://x")
    msg = str(ei.value)
    assert "cannot be applied" in msg
    assert "ZZZ" in msg


def test_apply_via_muiogo_unreachable(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="not reachable"):
        apply_via_muiogo({"case": "C"}, "REF", base_url="http://127.0.0.1:5000")


# --- CLI dry-run build against the real demo case (skips cleanly if absent) ----------

_DEMO_PARENT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "WebAPP", "DataStorage")
_DEMO = os.path.join(_DEMO_PARENT, "CLEWs Demo")


@pytest.mark.skipif(not os.path.isdir(_DEMO), reason="CLEWs Demo case not present")
def test_writeback_dry_run_builds_patch(tmp_path, monkeypatch):
    # ELC002 is the demo case's nonzero load carrier; point the country's demand_commodity at it.
    cfg = dataclasses.replace(country.PHL, demand_commodity="ELC002")
    monkeypatch.setattr(country, "resolve_country", lambda selector, config_file=None: cfg)

    # No network must happen in a dry run -- make any POST attempt fail loudly if it does.
    def _boom(*a, **k):
        raise AssertionError("dry-run must not POST")
    monkeypatch.setattr("urllib.request.urlopen", _boom)

    run = tmp_path / "run"
    (run / "clews_inputs").mkdir(parents=True)
    ds_csv = run / "clews_inputs" / "demand_scaling.csv"
    ds_csv.write_text(
        "REGION,OG_ACTIVITY,OG_INDEX,CLEWS_FUEL,YEAR,DEMAND_RATIO\n"
        "RE1,Y,0,ELC002,2030,1.050000\n"
        "RE1,Y,0,ELC002,2031,1.100000\n",
        encoding="utf-8")

    cli.main(["writeback", "--run", str(run), "--country", "phl",
              "--case", "CLEWs Demo", "--base-caserun", "REF",
              "--datastorage", os.path.abspath(_DEMO_PARENT), "--dry-run"])

    patch_path = run / "clews_patch.json"
    assert patch_path.is_file()
    patch = json.loads(patch_path.read_text(encoding="utf-8"))
    assert patch["case"] == "CLEWs Demo"
    by_year = {c["year"]: c for c in patch["changes"]}
    assert set(by_year) == {2030, 2031}
    for c in patch["changes"]:
        assert set(c) == {"group", "code", "year", "value", "scenario"}
        assert c["group"] == "Demand"
        assert c["code"] == "ELC002"
        assert c["scenario"] == "SC_0"
    # value = base_SAD * ratio, against the case's SC_0 row (341 in 2030, 365 in 2031).
    assert by_year[2030]["value"] == pytest.approx(341 * 1.05)
    assert by_year[2031]["value"] == pytest.approx(365 * 1.10)


@pytest.mark.slow
@pytest.mark.skipif(not os.environ.get("OGLINK_MUIOGO_URL"),
                    reason="live MUIOGO round-trip: set OGLINK_MUIOGO_URL to run")
def test_writeback_live_roundtrip():
    # Opt-in only: needs a running MUIOGO with a solved base caserun. The default suite
    # never requires a server.
    pytest.skip("live round-trip is a manual, environment-gated check")
