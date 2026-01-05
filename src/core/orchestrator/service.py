from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Iterable

from src.core.contracts import FinalSignal, OrderRequest
from src.core.data.market_data import MarketDataProvider
from src.core.data.validator import MarketDataValidator
from src.core.ensemble.aggregator import EnsembleAggregator
from src.core.execution.execution_service import ExecutionService
from src.core.execution.order_manager import OrderManager
from src.core.execution.slippage import SlippageModel
from src.core.features.feature_engine import FeatureEngine
from src.core.monitoring.alerts import AlertManager
from src.core.monitoring.circuit_breaker import CircuitBreaker
from src.core.monitoring.error_handler import ConnectivityError, DataValidationError, ErrorHandler
from src.core.monitoring.health import HealthMonitor
from src.core.monitoring.notifications import send_desktop_notification
from src.core.monitoring.performance import PerformanceMonitor
from src.core.portfolio.position_manager import PositionManager
from src.core.portfolio.snapshot import PortfolioSnapshot
from src.core.portfolio.trade_queue import TradeQueue
from src.core.risk.correlation import CorrelationManager
from src.core.risk.manager import RiskManager
from src.core.sentiment.provider import SentimentProvider
from src.core.settings import Settings
from src.core.storage.db import SQLiteStore
from src.core.strategies.strategies import build_strategies
from src.core.orchestrator.setup_gate import SetupGate


@dataclass
class Orchestrator:
    settings: Settings
    data_provider: MarketDataProvider
    feature_engine: FeatureEngine
    data_validator: MarketDataValidator
    ensemble: EnsembleAggregator
    risk_manager: RiskManager
    correlation_manager: CorrelationManager
    execution: ExecutionService
    order_manager: OrderManager
    slippage_model: SlippageModel
    store: SQLiteStore
    trade_queue: TradeQueue
    setup_gate: SetupGate
    health_monitor: HealthMonitor
    circuit_breaker: CircuitBreaker
    error_handler: ErrorHandler
    performance_monitor: PerformanceMonitor
    alert_manager: AlertManager
    sentiment_provider: SentimentProvider | None
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
        self.order_manager.purge_stale_orders()
        exit_actions = self.position_manager.evaluate_exits()
        for action in exit_actions:
            self.store.add_log("info", action)

        account = self.execution.client.get_account()
        portfolio = PortfolioSnapshot.from_account(account)
        equity = float(account.get("equity", portfolio.cash))
        exposure = 1 - (portfolio.cash / equity) if equity > 0 else 0.0
        self.performance_monitor.update_equity(equity, exposure)
        can_trade, reason = self.circuit_breaker.can_trade(
            drawdown=self.performance_monitor.drawdown(),
            connectivity_ok=True,
        )
        if not can_trade:
            self.alert_manager.send_alert("circuit_breaker", "Circuit Breaker", f"Trading halted: {reason}")
            return {"status": "halted", "processed": 0, "message": reason}
        if portfolio.cash / max(equity, 1) < self.settings.alerts.low_cash_threshold:
            self.alert_manager.send_alert(
                "low_cash",
                "Low Cash",
                f"Cash below threshold: ${portfolio.cash:.2f}",
            )
        open_positions = len(self.execution.client.list_positions())
        max_positions = self.settings.risk.max_open_positions

        processed = 0
        decisions = []
        cycle_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        for symbol in symbols:
            if open_positions >= max_positions:
                self.store.add_log("warning", "Max open positions reached; skipping new entries.")
                break
            processed += 1
            try:
                bars = self.data_provider.get_daily_bars(symbol, limit=160)
                bars = self.data_validator.preprocess(bars)
            except ValueError as exc:
                classification = self.error_handler.handle(DataValidationError(str(exc)), f"fetch/validate {symbol}")
                self.circuit_breaker.record_failure(classification)
                continue
            except Exception as exc:  # noqa: BLE001
                classification = self.error_handler.handle(ConnectivityError(str(exc)), f"fetch/validate {symbol}")
                self.circuit_breaker.record_failure(classification)
                continue
            features = self.feature_engine.compute(symbol, bars)
            allowed, reason = self.setup_gate.allow(features)
            if not allowed:
                self.store.add_log("info", f"Setup gate blocked {symbol}: {reason}")
                continue
            intents = []
            for strategy in build_strategies(self.settings.strategies):
                signal = strategy.generate(features)
                if signal:
                    intents.append(signal)
            final = self.ensemble.aggregate(intents)
            if final is None:
                self.store.add_log("info", f"No final signal for {symbol}.")
                continue
            if self.settings.sentiment.enabled and self.sentiment_provider:
                sentiment = self.sentiment_provider.get_sentiment(symbol)
                if sentiment.score < self.settings.sentiment.min_score:
                    self.store.add_log(
                        "warning",
                        f"Sentiment veto for {symbol}: score {sentiment.score:.2f}",
                    )
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
            candidate_weight = (decision.shares * final.entry) / max(portfolio.equity, 1)
            holdings = {pos["symbol"]: float(pos.get("market_value", 0)) / max(equity, 1) for pos in self.execution.client.list_positions()}
            price_history = {final.symbol: bars}
            for held_symbol in holdings:
                if held_symbol == final.symbol:
                    continue
                price_history[held_symbol] = self.data_provider.get_daily_bars(held_symbol, limit=160)
            corr_ok, corr_reason = self.correlation_manager.check_symbol(
                final.symbol,
                candidate_weight,
                holdings,
                price_history,
            )
            sector_ok, sector_reason = self.correlation_manager.check_sector(
                final.symbol,
                candidate_weight,
                holdings,
                sector_map=self.sector_map,
            )
            if not corr_ok or not sector_ok:
                self.store.add_log("warning", f"Correlation veto for {final.symbol}: {corr_reason or sector_reason}")
                continue
            idempotency_key = f"{cycle_id}-{final.symbol}-{decision.shares}"
            order = OrderRequest(
                symbol=final.symbol,
                side="buy",
                quantity=decision.shares,
                stop_loss=final.stop,
                take_profit=final.take_profit,
                idempotency_key=idempotency_key,
                client_order_id=idempotency_key,
            )
            est_cost = self.slippage_model.estimate_cost(final.entry, decision.shares)
            self.store.add_log("info", f"Estimated slippage+fees for {final.symbol}: ${est_cost:.2f}")
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
            self.performance_monitor.record_trade(-est_cost)
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
