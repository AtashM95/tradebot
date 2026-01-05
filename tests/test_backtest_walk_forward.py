from __future__ import annotations

import numpy as np
import pandas as pd

from src.core.backtest.walk_forward import WalkForwardBacktester


class DummyProvider:
    def __init__(self, bars: pd.DataFrame) -> None:
        self._bars = bars

    def get_daily_bars(self, symbol: str, limit: int = 200) -> pd.DataFrame:
        return self._bars.tail(limit)


def test_walk_forward_run_returns_metrics():
    rng = np.random.default_rng(7)
    rows = 120
    prices = np.linspace(100, 120, rows) + rng.normal(0, 0.5, rows)
    highs = prices + rng.uniform(0.5, 1.0, rows)
    lows = prices - rng.uniform(0.5, 1.0, rows)
    bars = pd.DataFrame(
        {
            "open": prices,
            "high": highs,
            "low": lows,
            "close": prices + rng.normal(0, 0.2, rows),
            "volume": rng.integers(900_000, 1_200_000, rows),
        }
    )
    provider = DummyProvider(bars)
    backtester = WalkForwardBacktester(data_provider=provider, train_days=40, test_days=20, step_days=20)
    report = backtester.run(["AAPL"], years=1)
    assert report["folds"]
    aggregate = report["aggregate"]
    for key in ["total_return", "max_drawdown", "win_rate", "profit_factor", "sharpe", "trades"]:
        assert key in aggregate
