from datetime import datetime, timezone

from src.core.data.alpaca_client import MockAlpacaClient
from src.core.data.cache import DataCache
from src.core.data.market_data import MarketDataProvider
from src.core.data.validator import MarketDataValidator
from src.core.ensemble.aggregator import EnsembleAggregator
from src.core.execution.execution_service import ExecutionService
from src.core.execution.order_manager import OrderManager
from src.core.execution.slippage import SlippageModel
from src.core.features.feature_engine import FeatureEngine
from src.core.monitoring.alerts import AlertManager
from src.core.monitoring.circuit_breaker import CircuitBreaker
from src.core.monitoring.error_handler import ErrorHandler
from src.core.monitoring.health import HealthMonitor
from src.core.monitoring.performance import PerformanceMonitor
from src.core.orchestrator.service import Orchestrator
from src.core.orchestrator.setup_gate import SetupGate
from src.core.portfolio.position_manager import PositionManager
from src.core.portfolio.trade_queue import TradeQueue
from src.core.risk.correlation import CorrelationManager
from src.core.risk.manager import RiskManager
from src.core.settings import FundingAlertSettings, RiskSettings, Settings, StorageSettings, TradingConstraints
from src.core.storage.db import SQLiteStore


def test_pipeline_dry_run(tmp_path):
    db_path = tmp_path / "tradebot.db"
    cache_dir = tmp_path / "cache"
    settings = Settings(
        storage=StorageSettings(database_url=f"sqlite:///{db_path}", cache_dir=str(cache_dir)),
        risk=RiskSettings(risk_per_trade=0.01, max_position_weight=0.2, cash_buffer=0.05),
        funding_alert=FundingAlertSettings(trade_queue_ttl_hours=24),
        trading=TradingConstraints(target_hold_days_max=14),
    )
    client = MockAlpacaClient()
    cache = DataCache(settings.storage.cache_dir)
    data_provider = MarketDataProvider(client=client, cache=cache)
    feature_engine = FeatureEngine()
    data_validator = MarketDataValidator()
    ensemble = EnsembleAggregator(min_score=0.5)
    risk_manager = RiskManager(
        risk_per_trade=settings.risk.risk_per_trade,
        max_position_weight=settings.risk.max_position_weight,
        cash_buffer=settings.risk.cash_buffer,
    )
    order_manager = OrderManager(client=client, ttl_minutes=10)
    execution = ExecutionService(settings=settings, client=client, order_manager=order_manager)
    slippage_model = SlippageModel(spread_bps=2.0, fee_bps=1.0)
    circuit_breaker = CircuitBreaker(max_failures=3, drawdown_limit=0.15, cooldown_minutes=30)
    error_handler = ErrorHandler(max_retries=2, retry_delay_seconds=1)
    performance_monitor = PerformanceMonitor()
    alert_manager = AlertManager(cooldown_seconds=0)
    correlation_manager = CorrelationManager(max_symbol_correlation=0.95, max_sector_weight=0.3)
    store = SQLiteStore(settings.storage.database_url)
    trade_queue = TradeQueue(store=store, ttl_hours=settings.funding_alert.trade_queue_ttl_hours)
    setup_gate = SetupGate(min_trend=-1.0, min_rsi=40.0)
    health_monitor = HealthMonitor(started_at=datetime.now(timezone.utc))
    position_manager = PositionManager(
        data_provider=data_provider,
        feature_engine=feature_engine,
        execution=execution,
        store=store,
        max_hold_days=settings.trading.target_hold_days_max,
        trailing_stop_enabled=False,
        trailing_atr_multiplier=2.5,
    )
    orchestrator = Orchestrator(
        settings=settings,
        data_provider=data_provider,
        feature_engine=feature_engine,
        data_validator=data_validator,
        ensemble=ensemble,
        risk_manager=risk_manager,
        correlation_manager=correlation_manager,
        execution=execution,
        order_manager=order_manager,
        slippage_model=slippage_model,
        store=store,
        trade_queue=trade_queue,
        setup_gate=setup_gate,
        health_monitor=health_monitor,
        circuit_breaker=circuit_breaker,
        error_handler=error_handler,
        performance_monitor=performance_monitor,
        alert_manager=alert_manager,
        position_manager=position_manager,
    )
    orchestrator.start()
    result = orchestrator.run_cycle(["AAPL"])
    assert result["processed"] == 1
