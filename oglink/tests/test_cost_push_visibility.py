"""The cost-push leg carries most of the electricity-price effect, so losing it must be visible:
an UNEXPECTED failure to compute the industry weights is recorded in the run's provenance rather
than silently dropped (a plain absence of a SAM still skips quietly)."""
import types

from oglink import experiments, framework


def test_electricity_intensity_logs_unexpected_failure():
    # a country whose OG model is not registered -> registry.lookup raises -> must log, then return None
    ctx = framework.ExperimentContext(
        country=types.SimpleNamespace(og_repo="no-such-model-xyz", og_package="nope"))
    phi = experiments._electricity_intensity(ctx)
    assert phi is None
    recs = [r for r in ctx.provenance if r.get("channel") == "electricity_intensity_unavailable"]
    assert recs, "an unexpected phi-source failure must leave a provenance record"
    assert recs[0].get("provenance_only") is True
    assert "reason" in recs[0]
