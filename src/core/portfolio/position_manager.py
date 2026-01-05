from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.core.contracts import OrderRequest
from src.core.data.market_data import MarketDataProvider
from src.core.execution.execution_service import ExecutionService
from src.core.features.feature_engine import FeatureEngine
from src.core.storage.db import SQLiteStore


@dataclass
class PositionManager:
    data_provider: MarketDataProvider
    feature_engine: FeatureEngine
    execution: ExecutionService
    store: SQLiteStore
    max_hold_days: int
    trailing_stop_enabled: bool
    trailing_atr_multiplier: float

    def evaluate_exits(self) -> list[str]:
        actions: list[str] = []
        open_trades = self.store.list_open_trades()
        for trade in open_trades:
            symbol = trade["symbol"]
            bars = self.data_provider.get_daily_bars(symbol, limit=120)
            features = self.feature_engine.compute(symbol, bars)
            latest_close = features.values["close"]
            stop = float(trade["stop"])
            take_profit = float(trade["take_profit"])
            opened_at = datetime.fromisoformat(trade["opened_at"])
            held_days = (datetime.now(timezone.utc) - opened_at).days
            if self.trailing_stop_enabled:
                atr = max(features.values.get("atr", 0.0), 0.01)
                new_stop = max(stop, latest_close - atr * self.trailing_atr_multiplier)
                if new_stop > stop:
                    self.store.update_trade_stop(int(trade["id"]), new_stop)
                    stop = new_stop
                    actions.append(f"Trailing stop updated for {symbol} -> {new_stop:.2f}")
            exit_reason = None
            if latest_close <= stop:
                exit_reason = "stop_loss"
            elif latest_close >= take_profit:
                exit_reason = "take_profit"
            elif held_days >= self.max_hold_days:
                exit_reason = "time_exit"

            if exit_reason:
                request = OrderRequest(symbol=symbol, side="sell", quantity=int(trade["quantity"]))
                self.execution.submit_order(request)
                self.store.close_trade(int(trade["id"]))
                actions.append(f"Exit {symbol} triggered by {exit_reason} at {latest_close:.2f}")
        return actions
