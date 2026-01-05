from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

import numpy as np
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest

from src.core.contracts import OrderRequest, OrderResult


@dataclass(frozen=True)
class AlpacaCredentials:
    api_key: str
    secret_key: str
    trading_base_url: str
    data_base_url: str


class AlpacaClient:
    def __init__(self, credentials: AlpacaCredentials, paper: bool = True) -> None:
        self._trading = TradingClient(
            credentials.api_key,
            credentials.secret_key,
            paper=paper,
            url_override=credentials.trading_base_url,
        )
        self._data = StockHistoricalDataClient(
            credentials.api_key,
            credentials.secret_key,
            url_override=credentials.data_base_url,
        )

    def get_account(self) -> dict:
        account = self._trading.get_account()
        return account.model_dump()

    def get_daily_bars(self, symbol: str, limit: int = 200) -> pd.DataFrame:
        request = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Day, limit=limit)
        response = self._data.get_stock_bars(request)
        bars = response.data.get(symbol, [])
        if not bars:
            raise ValueError(f"No bars returned for {symbol}.")
        df = pd.DataFrame([bar.model_dump() for bar in bars])
        df = df.rename(columns={"timestamp": "ts"})
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        return df[["ts", "open", "high", "low", "close", "volume"]]

    def submit_order(self, request: OrderRequest) -> OrderResult:
        order = MarketOrderRequest(
            symbol=request.symbol,
            qty=request.quantity,
            side=request.side,
            time_in_force=request.time_in_force,
        )
        response = self._trading.submit_order(order)
        data = response.model_dump()
        return OrderResult(
            order_id=str(data.get("id", "")),
            symbol=request.symbol,
            status=data.get("status", "unknown"),
            filled_qty=int(data.get("filled_qty", 0) or 0),
            average_fill_price=data.get("filled_avg_price"),
            raw={"alpaca": "true"},
        )

    def list_positions(self) -> list[dict]:
        positions = self._trading.get_all_positions()
        return [position.model_dump() for position in positions]


class MockAlpacaClient:
    def get_account(self) -> dict:
        return {
            "id": "mock-account",
            "cash": "100000",
            "equity": "100000",
            "status": "ACTIVE",
        }

    def get_daily_bars(self, symbol: str, limit: int = 200) -> pd.DataFrame:
        rng = np.random.default_rng(42)
        dates = pd.date_range(end=datetime.utcnow(), periods=limit, freq="B")
        base = np.linspace(100, 120, num=limit)
        noise = rng.normal(0, 0.5, size=limit)
        close = base + noise
        open_ = close + rng.normal(0, 0.3, size=limit)
        high = np.maximum(open_, close) + rng.uniform(0.1, 1.0, size=limit)
        low = np.minimum(open_, close) - rng.uniform(0.1, 1.0, size=limit)
        volume = rng.integers(900_000, 1_100_000, size=limit)
        return pd.DataFrame(
            {
                "ts": dates,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )

    def submit_order(self, request: OrderRequest) -> OrderResult:
        return OrderResult(
            order_id=f"mock-{uuid4()}",
            symbol=request.symbol,
            status="filled",
            filled_qty=request.quantity,
            average_fill_price=100.0,
            raw={"mock": "true"},
        )

    def list_positions(self) -> list[dict]:
        return []
