import pandas as pd

from src.core.risk.stress_tester import StressTester


def test_stress_tester_smoke():
    tester = StressTester()
    price_history = {"AAPL": pd.DataFrame({"close": [100.0, 101.0]})}
    weights = {"AAPL": 1.0}
    shocks = {"down_10": -0.1}
    results = tester.run(price_history, weights, shocks)
    assert results
    assert results[0].scenario == "down_10"
