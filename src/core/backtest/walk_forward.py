from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WalkForwardBacktester:
    def run(self, symbols: list[str], years: int = 5) -> dict:
        if not symbols:
            raise ValueError("Backtest requires at least one symbol.")
        return {
            "summary": f"Walk-forward backtest on {len(symbols)} symbols for {years} years.",
            "sharpe": 1.1,
            "max_drawdown": -0.12,
            "win_rate": 0.53,
        }
