from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class MarketDataValidator:
    outlier_quantile: float = 0.001

    def preprocess(self, bars: pd.DataFrame) -> pd.DataFrame:
        if bars is None or bars.empty:
            raise ValueError("Market data is empty.")
        df = bars.copy()
        if "ts" not in df.columns:
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index().rename(columns={"index": "ts"})
            else:
                raise ValueError("Market data must include 'ts' column.")
        required = ["ts", "open", "high", "low", "close", "volume"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Market data missing columns: {missing}")
        df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
        if df["ts"].isna().any():
            raise ValueError("Market data contains invalid timestamps.")
        df = df.sort_values("ts").reset_index(drop=True)
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df[numeric_cols] = df[numeric_cols].ffill().bfill()
        if df[numeric_cols].isna().any().any():
            raise ValueError("Market data contains NaN after fill policy.")
        if (df[["open", "high", "low", "close"]] <= 0).any().any():
            raise ValueError("Market data contains non-positive prices.")
        df = self._cap_outliers(df, numeric_cols)
        return df[required]

    def _cap_outliers(self, df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        logger = logging.getLogger(__name__)
        lower = self.outlier_quantile
        upper = 1 - self.outlier_quantile
        for col in cols:
            q_low = df[col].quantile(lower)
            q_high = df[col].quantile(upper)
            if q_low == q_high:
                continue
            before = df[col].copy()
            df[col] = df[col].clip(lower=q_low, upper=q_high)
            if not before.equals(df[col]):
                logger.info("Capped outliers in %s using quantiles %.3f/%.3f", col, lower, upper)
        return df
