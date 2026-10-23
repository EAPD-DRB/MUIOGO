"""Synthetic unit tests for the clews_patch.json builder, plus a light real-case pin
for the base-SAD reader against the CLEWs Demo case when it is present.
"""
import os

import pytest

from oglink import clews_case
from oglink.patch import build_clews_patch

YEARS = {2020, 2025, 2030, 2031, 2032}


def _base(**kw):
    args = dict(case="DemoCase", scenario="SC_0", demand_commodity="PHL_HOU_ELEF",
                case_years=YEARS, start_year=2026)
    args.update(kw)
    return build_clews_patch(**args)


def test_ratio_to_absolute():
    patch = _base(demand_ratio_by_year={2030: 1.1, 2031: 0.9},
                  base_sad_by_year={2030: 100.0, 2031: 200.0})
    by_year = {c["year"]: c for c in patch["changes"]}
    assert by_year[2030]["value"] == pytest.approx(110.0)
    assert by_year[2031]["value"] == pytest.approx(180.0)
    for c in patch["changes"]:
        assert c["group"] == "Demand"
        assert c["code"] == "PHL_HOU_ELEF"
        assert c["scenario"] == "SC_0"


def test_year_clip():
    # 2025 < start_year (dropped); 2099 not in case_years (dropped); 2030 kept
    patch = _base(demand_ratio_by_year={2025: 1.5, 2030: 1.2, 2099: 2.0},
                  base_sad_by_year={2025: 50.0, 2030: 100.0, 2099: 10.0})
    assert {c["year"] for c in patch["changes"]} == {2030}


def test_no_op_suppression():
    patch = _base(demand_ratio_by_year={2030: 1.0, 2031: 1.0 + 1e-12, 2032: 1.2},
                  base_sad_by_year={2030: 100.0, 2031: 100.0, 2032: 100.0})
    assert {c["year"] for c in patch["changes"]} == {2032}


def test_all_zero_base_guard():
    with pytest.raises(ValueError, match="all zero"):
        _base(demand_ratio_by_year={2030: 1.1},
              base_sad_by_year={2030: 0.0, 2031: 0.0})


def test_default_value_guard():
    with pytest.raises(ValueError, match="set demand to 0"):
        _base(demand_ratio_by_year={2030: 0.0},
              base_sad_by_year={2030: 100.0})


def test_deferred_passthrough_never_in_changes():
    deferred = [{"artifact": "DiscountRate", "region": "RE1", "value": 0.05}]
    patch = _base(demand_ratio_by_year={2030: 1.1},
                  base_sad_by_year={2030: 100.0}, deferred=deferred)
    assert patch["deferred"] == deferred
    assert all(c["group"] != "DiscountRate" for c in patch["changes"])


def test_missing_base_raises():
    with pytest.raises(ValueError, match="no base for"):
        _base(demand_ratio_by_year={2030: 1.1, 2031: 1.2},
              base_sad_by_year={2030: 100.0})


def test_emissions_penalty():
    patch = _base(demand_ratio_by_year={2030: 1.1},
                  base_sad_by_year={2030: 100.0},
                  emissions={"species": "CO2e",
                             "value_by_year": {2025: 40.0, 2030: 50.0, 2031: 60.0}})
    ep = [c for c in patch["changes"] if c["group"] == "EmissionsPenalty"]
    assert {c["year"]: c["value"] for c in ep} == {2030: 50.0, 2031: 60.0}  # 2025 clipped
    assert all(c["code"] == "CO2e" for c in ep)


def test_change_shape():
    patch = _base(demand_ratio_by_year={2030: 1.1},
                  base_sad_by_year={2030: 100.0})
    for c in patch["changes"]:
        assert set(c) == {"group", "code", "year", "value", "scenario"}
        assert isinstance(c["value"], float)
        assert isinstance(c["year"], int)


# --- real-case pin for the base-SAD reader (skips cleanly if the case is absent) ----

_DEMO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "..", "WebAPP", "DataStorage", "CLEWs Demo")


@pytest.mark.skipif(not os.path.isdir(_DEMO), reason="CLEWs Demo case not present")
def test_read_base_sad_real_case():
    load = clews_case.read_base_sad(_DEMO, "SC_0", "ELC002")
    assert load and all(isinstance(k, int) and isinstance(v, float) for k, v in load.items())
    assert any(v != 0 for v in load.values())  # ELC002 is the load carrier
    zero = clews_case.read_base_sad(_DEMO, "SC_0", "ELC001")
    assert all(v == 0 for v in zero.values())  # ELC001 is the zero carrier (the F1 distinction)
