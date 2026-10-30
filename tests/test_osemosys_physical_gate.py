from scripts.validate_osemosys_physical_gate import evaluate_slice, interval_term


def annual_result(demand: float, ceiling: float):
    return evaluate_slice(
        year="2030",
        timeslice="ANNUAL",
        year_split=1.0,
        direct_demand={"service": demand},
        technologies=("producer",),
        routes_by_output={"service": [("producer", 1, 1.0)]},
        inputs_by_route={},
        activity_ceiling={"producer": ceiling},
        tech_name={"producer": "GENERIC_PRODUCER"},
        commodity_name={"service": "GENERIC_SERVICE"},
    )


def test_annual_aad_envelope_passes_without_timeslice_profile():
    result = annual_result(demand=9.0, ceiling=10.0)
    assert result["status"] == "passed"
    assert result["failures"] == []
    assert result["forced_activity_lower_rate"] == {"producer": 9.0}


def test_annual_aad_envelope_reports_generic_shortfall():
    result = annual_result(demand=11.0, ceiling=10.0)
    assert result["status"] == "failed"
    assert result["failures"][0]["kind"] == "commodity_timeslice_shortfall"
    assert result["failures"][0]["commodity"] == "GENERIC_SERVICE"
    assert result["failures"][0]["headroom_rate"] == -1.0


def test_interval_term_respects_negative_coefficients():
    assert interval_term(2.0, 3.0, 5.0) == (6.0, 10.0)
    assert interval_term(-2.0, 3.0, 5.0) == (-10.0, -6.0)
