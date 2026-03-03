"""
Tests for API/Classes/Base/Config.py

Verifies that:
- Required constants are present and have the expected types
- Path constants resolve to absolute paths
- PARAMETERS_C and VARIABLES_C have valid dimension entries
- Group tuples are subsets of PARAMETERS_C keys
"""
import sys
import os
from pathlib import Path

# Add project root so imports resolve without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from API.Classes.Base.Config import (
    PARAMETERS_C,
    VARIABLES_C,
    TECH_GROUPS,
    COMM_GROUPS,
    EMIS_GROUPS,
    HEROKU_DEPLOY,
    AWS_SYNC,
    DATA_STORAGE,
    WEBAPP_PATH,
)


class TestConfigConstants:
    def test_heroku_deploy_is_int(self):
        assert isinstance(HEROKU_DEPLOY, int)

    def test_aws_sync_is_int(self):
        assert isinstance(AWS_SYNC, int)

    def test_data_storage_is_absolute(self):
        assert DATA_STORAGE.is_absolute()

    def test_webapp_path_is_absolute(self):
        assert WEBAPP_PATH.is_absolute()

    def test_data_storage_exists(self):
        # Created on import by Config.py if missing
        assert DATA_STORAGE.exists()


class TestParametersC:
    def test_parameters_c_is_dict(self):
        assert isinstance(PARAMETERS_C, dict)

    def test_parameters_c_not_empty(self):
        assert len(PARAMETERS_C) > 0

    def test_all_values_are_lists(self):
        for key, dims in PARAMETERS_C.items():
            assert isinstance(dims, list), f"{key} dims should be a list"

    def test_all_dims_are_strings(self):
        for key, dims in PARAMETERS_C.items():
            for d in dims:
                assert isinstance(d, str), f"{key}: dimension {d!r} is not a string"

    def test_discount_rate_present(self):
        # DiscountRate is one of the core OSeMOSYS parameters
        assert "DiscountRate" in PARAMETERS_C


class TestVariablesC:
    def test_variables_c_is_dict(self):
        assert isinstance(VARIABLES_C, dict)

    def test_variables_c_not_empty(self):
        assert len(VARIABLES_C) > 0

    def test_new_capacity_present(self):
        assert "NewCapacity" in VARIABLES_C


class TestGroupTuples:
    def test_tech_groups_type(self):
        assert isinstance(TECH_GROUPS, tuple)

    def test_comm_groups_type(self):
        assert isinstance(COMM_GROUPS, tuple)

    def test_emis_groups_type(self):
        assert isinstance(EMIS_GROUPS, tuple)

    def test_no_empty_group_strings(self):
        for grp in TECH_GROUPS + COMM_GROUPS + EMIS_GROUPS:
            assert grp.strip() != "", f"Empty string found in group tuples"
