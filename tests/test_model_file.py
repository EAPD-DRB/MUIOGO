"""Guards on the shared OSeMOSYS model file.

The plain EBb4 energy-balance constraint duplicated the _ICR variant row for
row (identically wherever no capacity-input terms apply, dominated otherwise),
so the solver could attach the energy-balance shadow price to the copy the app
never reads and the Duals view showed 0 instead of the real value. The twin was
removed; this guards against it being reintroduced, e.g. by an upstream sync.
"""

from pathlib import Path

MODEL = Path(__file__).resolve().parents[1] / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"


def test_model_file_has_no_redundant_ebb4_twin():
    model = MODEL.read_text()
    # The variant the app reads shadow prices from must exist...
    assert "s.t. EBb4_EnergyBalanceEachYear4_ICR" in model
    # ...and the redundant plain twin must not come back.
    assert "\ns.t. EBb4_EnergyBalanceEachYear4{" not in model
