from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class CorrelationManager:
    max_symbol_correlation: float
    max_sector_weight: float
    window: int = 60

    def check_symbol(
        self,
        candidate: str,
        candidate_weight: float,
        holdings: dict[str, float],
        price_history: dict[str, pd.DataFrame],
    ) -> tuple[bool, str]:
        if not holdings:
            return True, "no_holdings"
        candidates = {candidate: price_history.get(candidate)}
        for symbol, df in price_history.items():
            if symbol in holdings and df is not None:
                candidates[symbol] = df
        if candidate not in candidates or candidates[candidate] is None:
            return True, "no_history"
        closes = {}
        for symbol, df in candidates.items():
            if df is None or "close" not in df.columns:
                continue
            closes[symbol] = df["close"].tail(self.window).pct_change().dropna()
        if candidate not in closes:
            return True, "no_returns"
        for symbol, returns in closes.items():
            if symbol == candidate:
                continue
            aligned = pd.concat([closes[candidate], returns], axis=1).dropna()
            if aligned.empty:
                continue
            corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
            if corr is not None and corr >= self.max_symbol_correlation:
                return False, f"correlation {corr:.2f} with {symbol}"
        return True, "ok"

    def check_sector(
        self,
        candidate: str,
        candidate_weight: float,
        holdings: dict[str, float],
        sector_map: dict[str, str],
    ) -> tuple[bool, str]:
        if not sector_map:
            return True, "no_sector_map"
        sector = sector_map.get(candidate)
        if not sector:
            return True, "unknown_sector"
        sector_weight = candidate_weight
        for symbol, weight in holdings.items():
            if sector_map.get(symbol) == sector:
                sector_weight += weight
        if sector_weight > self.max_sector_weight:
            return False, f"sector_weight {sector_weight:.2f} exceeds limit"
        return True, "ok"
