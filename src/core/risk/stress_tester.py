from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class StressTestResult:
    scenario: str
    portfolio_return: float
    details: dict[str, float]


@dataclass
class StressTester:
    def run(
        self,
        price_history: dict[str, pd.DataFrame],
        weights: dict[str, float],
        shocks: dict[str, float],
    ) -> list[StressTestResult]:
        results: list[StressTestResult] = []
        for scenario, shock in shocks.items():
            impact = {}
            portfolio_return = 0.0
            for symbol, weight in weights.items():
                df = price_history.get(symbol)
                if df is None or df.empty:
                    impact[symbol] = 0.0
                    continue
                last_close = float(df["close"].iloc[-1])
                stressed_price = last_close * (1 + shock)
                symbol_return = (stressed_price - last_close) / last_close
                impact[symbol] = symbol_return
                portfolio_return += symbol_return * weight
            results.append(
                StressTestResult(
                    scenario=scenario,
                    portfolio_return=portfolio_return,
                    details=impact,
                )
            )
        return results
