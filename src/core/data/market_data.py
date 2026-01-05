from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.core.data.cache import DataCache


@dataclass
class MarketDataProvider:
    client: object
    cache: DataCache

    def get_daily_bars(self, symbol: str, limit: int = 200) -> pd.DataFrame:
        cached = self.cache.load_daily_bars(symbol, limit)
        if cached is not None and not cached.empty:
            return cached
        bars = self.client.get_daily_bars(symbol, limit=limit)
        self.cache.save_daily_bars(symbol, bars)
        return bars

    def get_daily_bars_batch(self, symbols: list[str], limit: int = 200) -> dict[str, pd.DataFrame]:
        results: dict[str, pd.DataFrame] = {}
        missing: list[str] = []
        for symbol in symbols:
            cached = self.cache.load_daily_bars(symbol, limit)
            if cached is not None and not cached.empty:
                results[symbol] = cached
            else:
                missing.append(symbol)
        if not missing:
            return results
        if hasattr(self.client, "get_daily_bars_batch"):
            fetched = self.client.get_daily_bars_batch(missing, limit=limit)
        else:
            fetched = {symbol: self.client.get_daily_bars(symbol, limit=limit) for symbol in missing}
        for symbol in missing:
            bars = fetched.get(symbol)
            if bars is None or bars.empty:
                raise ValueError(f"No bars returned for {symbol}.")
            self.cache.save_daily_bars(symbol, bars)
            results[symbol] = bars
        return results
