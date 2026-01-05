import pandas as pd

from src.core.risk.correlation import CorrelationManager


def test_correlation_manager_blocks_high_corr():
    manager = CorrelationManager(max_symbol_correlation=0.5, max_sector_weight=0.3, window=5)
    returns = [100, 101, 102, 103, 104, 105]
    df = pd.DataFrame({"close": returns})
    holdings = {"MSFT": 0.2}
    price_history = {"AAPL": df, "MSFT": df}
    allowed, reason = manager.check_symbol("AAPL", 0.1, holdings, price_history)
    assert allowed is False
    assert "correlation" in reason


def test_correlation_manager_allows_sector_within_limit():
    manager = CorrelationManager(max_symbol_correlation=0.9, max_sector_weight=0.4, window=5)
    holdings = {"MSFT": 0.2}
    allowed, _ = manager.check_sector(
        "AAPL",
        candidate_weight=0.1,
        holdings=holdings,
        sector_map={"AAPL": "tech", "MSFT": "tech"},
    )
    assert allowed is True
