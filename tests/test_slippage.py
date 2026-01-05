import pytest

from src.core.execution.slippage import SlippageModel


def test_slippage_model_estimates_cost():
    model = SlippageModel(spread_bps=2.0, fee_bps=1.0)
    cost = model.estimate_cost(price=100.0, shares=10)
    assert cost == pytest.approx(0.3)
