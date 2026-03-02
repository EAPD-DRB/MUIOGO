"""
tests/test_parameter_iterator.py
==================================
pytest suite for ParameterIterator — the Cartesian Product Engine.

Run:
    pytest tests/test_parameter_iterator.py -v
"""

import pytest
import itertools
from API.Classes.Base.ParameterIterator import (
    ParameterIterator,
    _resolve_axis,
    _cartesian_axes,
    _iter_combinations,
    _year_list,
    _DIM_SPECS,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

YEARS    = ["2020", "2021", "2022"]
REGIONS  = [{"RegionId": "RE1"}]
TECHS    = [{"TechId": "T1"}, {"TechId": "T2"}]
STGS     = [{"StgId": "STG_A"}, {"StgId": "STG_B"}]
COMMS    = [{"CommId": "C1"}]
SCENARIOS = [
    {"ScenarioId": "SC_0"},
    {"ScenarioId": "SC_1"},
]

GEN_DATA = {
    "osy-years":     YEARS,
    "osy-region":    REGIONS,
    "osy-tech":      TECHS,
    "osy-stg":       STGS,
    "osy-comm":      COMMS,
    "osy-scenarios": SCENARIOS,
    "osy-mo":        "2",   # modes: 1, 2
}

PARAMS_RYT = [
    {"id": "FC", "value": "Fixed Cost",    "default": 0.0},
    {"id": "CC", "value": "Capital Cost",  "default": 1.0},
]

PARAMS_RYTM = [
    {"id": "VC", "value": "Variable Cost", "default": 0.0001},
]

PARAMS_RYTSM = [
    {"id": "TAR", "value": "Tech Activity Rate", "default": 0.5},
]


# ---------------------------------------------------------------------------
# _resolve_axis
# ---------------------------------------------------------------------------

class TestResolveAxis:
    def test_tech_axis(self):
        result = _resolve_axis("T", GEN_DATA)
        assert result == TECHS

    def test_mode_axis_is_range(self):
        # osy-mo = "2" → modes [1, 2]
        result = _resolve_axis("M", GEN_DATA)
        assert result == [1, 2]

    def test_year_axis(self):
        result = _resolve_axis("Y", GEN_DATA)
        assert result == YEARS

    def test_unknown_char_raises(self):
        with pytest.raises(ValueError, match="unknown dimension"):
            _resolve_axis("Z", GEN_DATA)

    def test_absent_key_returns_empty_and_warns(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING):
            result = _resolve_axis("R", {"osy-tech": TECHS})  # osy-region absent
        assert result == []
        assert any("absent" in r.message for r in caplog.records)

    def test_bad_mode_value_raises(self):
        with pytest.raises(ValueError, match="osy-mo"):
            _resolve_axis("M", {**GEN_DATA, "osy-mo": "not_a_number"})


# ---------------------------------------------------------------------------
# _cartesian_axes + _iter_combinations
# ---------------------------------------------------------------------------

class TestCartesianAxes:
    def test_ryt_excludes_year(self):
        chars, axes = _cartesian_axes("RYT", GEN_DATA)
        assert "Y" not in chars
        assert "R" in chars
        assert "T" in chars

    def test_rytm_axes(self):
        chars, axes = _cartesian_axes("RYTM", GEN_DATA)
        assert set(chars) == {"R", "T", "M"}

    def test_combination_count_ryt(self):
        chars, axes = _cartesian_axes("RYT", GEN_DATA)
        expected = len(REGIONS) * len(TECHS)
        combos = list(_iter_combinations(chars, axes))
        assert len(combos) == expected

    def test_combination_count_rytm(self):
        chars, axes = _cartesian_axes("RYTM", GEN_DATA)
        # R=1, T=2, M=2 → 4 combos
        expected = 1 * 2 * 2
        combos = list(_iter_combinations(chars, axes))
        assert len(combos) == expected

    def test_combination_count_rytsm(self):
        chars, axes = _cartesian_axes("RYTSM", GEN_DATA)
        # R=1, T=2, S=2, M=2 → 8 combos
        expected = 1 * 2 * 2 * 2
        combos = list(_iter_combinations(chars, axes))
        assert len(combos) == expected

    def test_chunk_keys_present(self):
        chars, axes = _cartesian_axes("RT", GEN_DATA)
        combos = list(_iter_combinations(chars, axes))
        for combo in combos:
            assert "RegionId" in combo
            assert "TechId"   in combo

    def test_year_only_group_yields_one_empty_combo(self):
        # Degenerate: group_key = "Y"  (unlikely but must not crash)
        chars, axes = _cartesian_axes("Y", GEN_DATA)
        combos = list(_iter_combinations(chars, axes))
        assert combos == [{}]

    def test_uses_itertools_product(self):
        """Verify the engine delegates to itertools.product (senior solution)."""
        import API.Classes.Base.ParameterIterator as mod
        import inspect
        src = inspect.getsource(mod._iter_combinations)
        assert "itertools.product" in src


# ---------------------------------------------------------------------------
# build_default — structure
# ---------------------------------------------------------------------------

class TestBuildDefault:
    @pytest.fixture
    def ryt_default(self):
        return ParameterIterator.build_default(
            group_key       = "RYT",
            parameters      = PARAMS_RYT,
            gen_data        = GEN_DATA,
            scenarios       = SCENARIOS,
            scenario_id_key = "ScenarioId",
            base_scenario   = "SC_0",
        )

    def test_top_level_keys_are_param_ids(self, ryt_default):
        assert set(ryt_default.keys()) == {"FC", "CC"}

    def test_second_level_keys_are_scenario_ids(self, ryt_default):
        assert set(ryt_default["FC"].keys()) == {"SC_0", "SC_1"}

    def test_third_level_is_list(self, ryt_default):
        assert isinstance(ryt_default["FC"]["SC_0"], list)

    def test_chunk_count_matches_cartesian_product(self, ryt_default):
        # R=1, T=2 → 2 chunks per scenario
        assert len(ryt_default["FC"]["SC_0"]) == 1 * 2

    def test_base_scenario_gets_default_value(self, ryt_default):
        for chunk in ryt_default["FC"]["SC_0"]:
            for year in YEARS:
                assert chunk[year] == 0.0   # FC default

    def test_non_base_scenario_gets_none(self, ryt_default):
        for chunk in ryt_default["FC"]["SC_1"]:
            for year in YEARS:
                assert chunk[year] is None

    def test_years_are_flat_keys_not_nesting(self, ryt_default):
        """Years must be flat keys inside each chunk, never a nesting level."""
        chunk = ryt_default["FC"]["SC_0"][0]
        for year in YEARS:
            assert year in chunk
        # Ensure no year-keyed sub-dict
        for year in YEARS:
            assert not isinstance(chunk[year], dict)

    def test_identity_keys_present(self, ryt_default):
        chunk = ryt_default["FC"]["SC_0"][0]
        assert "TechId"   in chunk
        assert "RegionId" in chunk

    def test_correct_default_per_param(self, ryt_default):
        # CC has default=1.0
        for chunk in ryt_default["CC"]["SC_0"]:
            for year in YEARS:
                assert chunk[year] == 1.0


class TestBuildDefaultRYTM:
    @pytest.fixture
    def rytm_default(self):
        return ParameterIterator.build_default(
            group_key       = "RYTM",
            parameters      = PARAMS_RYTM,
            gen_data        = GEN_DATA,
            scenarios       = SCENARIOS,
            scenario_id_key = "ScenarioId",
        )

    def test_chunk_count(self, rytm_default):
        # R=1, T=2, M=2 → 4 chunks
        assert len(rytm_default["VC"]["SC_0"]) == 4

    def test_mode_id_in_chunk(self, rytm_default):
        chunks = rytm_default["VC"]["SC_0"]
        mode_ids = {c["MoId"] for c in chunks}
        assert mode_ids == {1, 2}

    def test_stg_id_not_in_chunk(self, rytm_default):
        # RYTM has no S dimension
        for chunk in rytm_default["VC"]["SC_0"]:
            assert "StgId" not in chunk


class TestBuildDefaultRYTSM:
    @pytest.fixture
    def rytsm_default(self):
        return ParameterIterator.build_default(
            group_key       = "RYTSM",
            parameters      = PARAMS_RYTSM,
            gen_data        = GEN_DATA,
            scenarios       = SCENARIOS,
            scenario_id_key = "ScenarioId",
        )

    def test_chunk_count(self, rytsm_default):
        # R=1, T=2, S=2, M=2 → 8 chunks
        assert len(rytsm_default["TAR"]["SC_0"]) == 8

    def test_all_identity_keys_present(self, rytsm_default):
        for chunk in rytsm_default["TAR"]["SC_0"]:
            assert "RegionId" in chunk
            assert "TechId"   in chunk
            assert "StgId"    in chunk
            assert "MoId"     in chunk

    def test_default_values_correct(self, rytsm_default):
        for chunk in rytsm_default["TAR"]["SC_0"]:
            for year in YEARS:
                assert chunk[year] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# build_update — value preservation
# ---------------------------------------------------------------------------

class TestBuildUpdate:
    @pytest.fixture
    def existing_ryt(self):
        """
        Simulates the output of OsemosysClass.RYT() normaliser.
        Structure: {param_id: {sc_id: {year: {tech_id: value}}}}
        """
        return {
            "FC": {
                "SC_0": {
                    year: {
                        tech["TechId"]: {
                            region["RegionId"]: 99.9
                            for region in REGIONS
                        }
                        for tech in TECHS
                    }
                    for year in YEARS
                },
                "SC_1": {}
            }
        }

    def test_existing_values_preserved(self, existing_ryt):
        def keys_exists(data, *keys):
            node = data
            for key in keys:
                if not isinstance(node, dict) or key not in node:
                    return False
                node = node[key]
            return True

        result = ParameterIterator.build_update(
            group_key       = "RYT",
            parameters      = PARAMS_RYT[:1],   # just FC
            gen_data        = GEN_DATA,
            scenarios       = SCENARIOS,
            existing_data   = existing_ryt,
            scenario_id_key = "ScenarioId",
            keys_exists_fn  = keys_exists,
        )
        # SC_0 has stored data → should be 99.9
        for chunk in result["FC"]["SC_0"]:
            for year in YEARS:
                assert chunk[year] == pytest.approx(99.9)

    def test_missing_values_fall_back_to_default(self):
        result = ParameterIterator.build_update(
            group_key       = "RYT",
            parameters      = PARAMS_RYT[:1],
            gen_data        = GEN_DATA,
            scenarios       = SCENARIOS,
            existing_data   = {},               # empty — nothing stored
            scenario_id_key = "ScenarioId",
        )
        for chunk in result["FC"]["SC_0"]:
            for year in YEARS:
                assert chunk[year] == 0.0   # FC default

    def test_non_base_scenario_missing_gets_none(self):
        result = ParameterIterator.build_update(
            group_key       = "RYT",
            parameters      = PARAMS_RYT[:1],
            gen_data        = GEN_DATA,
            scenarios       = SCENARIOS,
            existing_data   = {},
        )
        for chunk in result["FC"]["SC_1"]:
            for year in YEARS:
                assert chunk[year] is None


# ---------------------------------------------------------------------------
# register_dimension (extensibility)
# ---------------------------------------------------------------------------

class TestRegisterDimension:
    def test_register_new_dimension(self):
        ParameterIterator.register_dimension(
            char         = "F",
            gendata_key  = "osy-fuel",
            chunk_key    = "FuelId",
            id_extractor = lambda item: item["FuelId"],
        )
        assert "F" in _DIM_SPECS
        assert _DIM_SPECS["F"].gendata_key == "osy-fuel"

    def test_new_dimension_used_in_build(self):
        ParameterIterator.register_dimension(
            char         = "F",
            gendata_key  = "osy-fuel",
            chunk_key    = "FuelId",
            id_extractor = lambda item: item["FuelId"],
        )
        gen_data_with_fuel = {
            **GEN_DATA,
            "osy-fuel": [{"FuelId": "FUEL_1"}, {"FuelId": "FUEL_2"}],
        }
        result = ParameterIterator.build_default(
            group_key       = "RTF",
            parameters      = [{"id": "XX", "value": "Test", "default": 0.0}],
            gen_data        = gen_data_with_fuel,
            scenarios       = SCENARIOS,
            scenario_id_key = "ScenarioId",
        )
        # R=1, T=2, F=2 → 4 chunks
        assert len(result["XX"]["SC_0"]) == 4
        for chunk in result["XX"]["SC_0"]:
            assert "FuelId" in chunk

    def teardown_method(self):
        # Clean up injected test dimension
        _DIM_SPECS.pop("F", None)


# ---------------------------------------------------------------------------
# describe_group (introspection)
# ---------------------------------------------------------------------------

class TestDescribeGroup:
    def test_describe_ryt(self):
        info = ParameterIterator.describe_group("RYT", GEN_DATA)
        assert info["group_key"]    == "RYT"
        assert info["year_count"]   == len(YEARS)
        assert info["combinations"] == 1 * 2   # R=1, T=2
        assert set(info["dimensions"]) == {"R", "T"}

    def test_describe_rytm(self):
        info = ParameterIterator.describe_group("RYTM", GEN_DATA)
        assert info["combinations"] == 1 * 2 * 2   # R=1, T=2, M=2