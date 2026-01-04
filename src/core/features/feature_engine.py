from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.core.contracts import Features


@dataclass
class FeatureEngine:
    atr_period: int = 14
    rsi_period: int = 14
    ema_fast: int = 12
    ema_slow: int = 26

    def compute(self, symbol: str, bars: pd.DataFrame) -> Features:
        df = bars.copy()
        df["prev_close"] = df["close"].shift(1)
        tr = pd.concat(
            [
                (df["high"] - df["low"]).abs(),
                (df["high"] - df["prev_close"]).abs(),
                (df["low"] - df["prev_close"]).abs(),
            ],
            axis=1,
        ).max(axis=1)
        df["atr"] = tr.rolling(self.atr_period).mean()
        delta = df["close"].diff()
        gain = delta.clip(lower=0).rolling(self.rsi_period).mean()
        loss = -delta.clip(upper=0).rolling(self.rsi_period).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["ema_fast"] = df["close"].ewm(span=self.ema_fast, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=self.ema_slow, adjust=False).mean()
        df["trend"] = df["ema_fast"] - df["ema_slow"]
        df["vol_avg"] = df["volume"].rolling(20).mean()
        latest = df.iloc[-1].fillna(0)
        values = {
            "close": float(latest["close"]),
            "atr": float(latest["atr"]),
            "rsi": float(latest["rsi"]),
            "ema_fast": float(latest["ema_fast"]),
            "ema_slow": float(latest["ema_slow"]),
            "trend": float(latest["trend"]),
            "vol_avg": float(latest["vol_avg"]),
        }
        return Features(symbol=symbol, values=values)
