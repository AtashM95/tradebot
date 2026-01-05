from src.core.portfolio.snapshot import PortfolioSnapshot


def test_portfolio_snapshot_prefers_equity():
    snapshot = PortfolioSnapshot.from_account(
        {"cash": "100.0", "portfolio_value": "120.0", "equity": "150.0", "positions": 3}
    )
    assert snapshot.cash == 100.0
    assert snapshot.equity == 150.0
    assert snapshot.open_positions == 3
