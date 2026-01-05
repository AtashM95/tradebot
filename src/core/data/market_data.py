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
