"""Unit tests for clews_io: the OG->CLEWS artifact writers. clews_io had no coverage, which let a
renamed Demand key (driver -> og_activity) slip past the suite. These check each writer's CSV header
and values directly, and that write_all dispatches every artifact the channels emit. Run with:

    PYTHONPATH=/Users/mlafleur/Projects/oglink \
      /Users/mlafleur/Projects/OG-PHL/.venv/bin/python -m pytest tests/test_clews_io.py
"""
from __future__ import annotations

import csv
import os
import tempfile
import types

from oglink import clews_io


def _read(path):
    with open(path, newline="") as f:
        return list(csv.reader(f))


# specs exactly as the channels emit them (channels.emit_energy_demand / emit_carbon_penalty /
# emit_discount_rate); these are the contract clews_io must keep reading.
_DEMAND = {"og_activity": "sector_output", "og_index": 1, "clews_fuel": None,
           "start_year": 2026, "ratio_by_period": [1.05, 1.04, 1.03]}
_PENALTY = {"region": "RE1", "emission": "CO2e", "start_year": 2026, "value_by_period": [50.0, 50.0]}
_RATE = {"region": "RE1", "rate": 0.05, "key": "r_p", "convention": "real; OG market cost of capital"}


def test_write_demand_header_and_values():
    with tempfile.TemporaryDirectory() as d:
        rows = _read(clews_io.write_demand(_DEMAND, d))
    assert rows[0] == ["REGION", "OG_ACTIVITY", "OG_INDEX", "CLEWS_FUEL", "YEAR", "DEMAND_RATIO"]
    assert len(rows) == 1 + len(_DEMAND["ratio_by_period"])           # header + one row per period
    assert rows[1][1] == "sector_output" and rows[1][2] == "1"       # og_activity, og_index
    assert rows[1][4] == "2026" and rows[1][5] == "1.050000"         # year, ratio (start_year, first ratio)


def test_write_emissions_penalty_header_and_values():
    with tempfile.TemporaryDirectory() as d:
        rows = _read(clews_io.write_emissions_penalty(_PENALTY, d))
    assert rows[0] == ["REGION", "EMISSION", "YEAR", "VALUE"]
    assert rows[1] == ["RE1", "CO2e", "2026", "50.000000"]


def test_write_discount_rate_scalar_and_path():
    with tempfile.TemporaryDirectory() as d:
        rows = _read(clews_io.write_discount_rate(_RATE, d))
    assert rows[0] == ["REGION", "VALUE", "NOTE"]
    assert rows[1][0] == "RE1" and rows[1][1] == "0.050000"
    # a full-path rate (list) writes the period-0 value and flags the path
    with tempfile.TemporaryDirectory() as d:
        rows = _read(clews_io.write_discount_rate({**_RATE, "rate": [0.05, 0.051]}, d))
    assert rows[1][1] == 0.05 or rows[1][1] == "0.05"               # period-0 value
    assert "path available" in rows[1][2]


def test_write_all_dispatches_every_artifact():
    ctx = types.SimpleNamespace(clews_inputs={"Demand": _DEMAND, "EmissionsPenalty": _PENALTY,
                                              "DiscountRate": _RATE, "Unknown": {"x": 1}})
    with tempfile.TemporaryDirectory() as d:
        written = clews_io.write_all(ctx, d)
        assert set(written) == {"Demand", "EmissionsPenalty", "DiscountRate"}  # Unknown ignored, no crash
        assert all(os.path.isfile(p) for p in written.values())


def main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn(); print("PASS", fn.__name__)


if __name__ == "__main__":
    main()
