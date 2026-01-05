from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable

from src.core.contracts import FinalSignal, OrderRequest
from src.core.data.market_data import MarketDataProvider
from src.core.ensemble.aggregator import EnsembleAggregator
from src.core.execution.execution_service import ExecutionService
from src.core.features.feature_engine import FeatureEngine
from src.core.monitoring.health import HealthMonitor
from src.core.monitoring.notifications import send_desktop_notification
from src.core.portfolio.position_manager import PositionManager
from src.core.portfolio.snapshot import PortfolioSnapshot
from src.core.portfolio.trade_queue import TradeQueue
from src.core.risk.manager import RiskManager
from src.core.settings import Settings
from src.core.storage.db import SQLiteStore
from src.core.strategies.strategies import build_strategies
from src.core.orchestrator.setup_gate import SetupGate


@dataclass
class Orchestrator:
    settings: Settings
    data_provider: MarketDataProvider
    feature_engine: FeatureEngine
    ensemble: EnsembleAggregator
    risk_manager: RiskManager
    execution: ExecutionService
    store: SQLiteStore
    trade_queue: TradeQueue
    setup_gate: SetupGate
    health_monitor: HealthMonitor
    position_manager: PositionManager
    status: str = "stopped"
    last_run_summary: dict = field(default_factory=dict)

    def start(self) -> None:
        self.status = "running"
        self.store.add_log("info", "Orchestrator started.")

    def pause(self) -> None:
        self.status = "paused"
        self.store.add_log("warning", "Orchestrator paused.")

    def stop(self) -> None:
        self.status = "stopped"
        self.store.add_log("warning", "Orchestrator stopped.")

    def run_cycle(self, symbols: Iterable[str]) -> dict:
        if self.status != "running":
            return {"status": self.status, "processed": 0, "message": "Orchestrator not running."}

        self.store.add_log("info", "Starting analysis cycle.")
        self.health_monitor.tick()
        exit_actions = self.position_manager.evaluate_exits()
        for action in exit_actions:
            self.store.add_log("info", action)

        account = self.execution.client.get_account()
        portfolio = PortfolioSnapshot.from_account(account)
        open_positions = len(self.execution.client.list_positions())
        max_positions = self.settings.risk.max_open_positions

        processed = 0
        decisions = []
        for symbol in symbols:
            if open_positions >= max_positions:
                self.store.add_log("warning", "Max open positions reached; skipping new entries.")
                break
            processed += 1
            bars = self.data_provider.get_daily_bars(symbol, limit=160)
            features = self.feature_engine.compute(symbol, bars)
            allowed, reason = self.setup_gate.allow(features)
            if not allowed:
                self.store.add_log("info", f"Setup gate blocked {symbol}: {reason}")
                continue
            intents = []
            for strategy in build_strategies():
                signal = strategy.generate(features)
                if signal:
                    intents.append(signal)
            final = self.ensemble.aggregate(intents)
            if final is None:
                self.store.add_log("info", f"No final signal for {symbol}.")
                continue
            self.store.add_signal(
                symbol=final.symbol,
                score=final.score,
                entry=final.entry,
                stop=final.stop,
                take_profit=final.take_profit,
                reasons=", ".join(final.reasons),
            )
            decision, funding = self.risk_manager.evaluate(final, portfolio)
            decisions.append(decision.model_dump())
            if funding:
                self.store.add_funding_alert(
                    symbol=final.symbol,
                    missing_cash=funding.missing_cash,
                    proposed_actions=", ".join(funding.proposed_actions),
                    details=json.dumps(funding.details),
                )
                self.trade_queue.enqueue(final.symbol, final.model_dump())
                if self.settings.notifications_enabled and self.settings.funding_alert.desktop_notifications:
                    notification = send_desktop_notification(
                        "Funding Alert",
                        f"{final.symbol}: missing ${funding.missing_cash:.2f}",
                    )
                    self.store.add_log("info", f"Desktop notify: {notification.detail}")
                self.store.add_log("warning", f"Funding alert for {final.symbol}; queued trade.")
                continue
            if not decision.approved:
                self.store.add_log("warning", f"Risk veto for {final.symbol}: {decision.reasons}")
                continue
            order = OrderRequest(
                symbol=final.symbol,
                side="buy",
                quantity=decision.shares,
                stop_loss=final.stop,
                take_profit=final.take_profit,
            )
            result = self.execution.submit_order(order)
            if result.status == "blocked":
                self.store.add_log("warning", f"Order blocked for {final.symbol} (mock mode).")
                continue
            trade_id = self.store.add_trade(
                symbol=final.symbol,
                side="buy",
                quantity=decision.shares,
                entry=final.entry,
                stop=final.stop,
                take_profit=final.take_profit,
            )
            self.store.add_fill(trade_id, final.symbol, decision.shares, final.entry)
            open_positions += 1
            self.store.add_log("info", f"Bracket order submitted for {final.symbol}.")
        self.last_run_summary = {
            "status": "completed",
            "processed": processed,
            "decisions": decisions,
            "exit_actions": exit_actions,
        }
        return self.last_run_summary

    def mock_mode(self) -> bool:
        return bool(getattr(self.execution.client, "is_mock", False))
