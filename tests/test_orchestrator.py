from datetime import datetime

from src.core.data.alpaca_client import MockAlpacaClient
from src.core.data.cache import DataCache
from src.core.data.market_data import MarketDataProvider
from src.core.ensemble.aggregator import EnsembleAggregator
from src.core.execution.execution_service import ExecutionService
from src.core.features.feature_engine import FeatureEngine
from src.core.monitoring.health import HealthMonitor
from src.core.orchestrator.service import Orchestrator
from src.core.orchestrator.setup_gate import SetupGate
from src.core.portfolio.position_manager import PositionManager
from src.core.portfolio.trade_queue import TradeQueue
from src.core.risk.manager import RiskManager
from src.core.settings import FundingAlertSettings, RiskSettings, Settings, StorageSettings, TradingConstraints
from src.core.storage.db import SQLiteStore


def test_orchestrator_cycle_with_mock(tmp_path):
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
    ensemble = EnsembleAggregator(min_score=0.5)
    risk_manager = RiskManager(
        risk_per_trade=settings.risk.risk_per_trade,
        max_position_weight=settings.risk.max_position_weight,
        cash_buffer=settings.risk.cash_buffer,
    )
    execution = ExecutionService(settings=settings, client=client)
    store = SQLiteStore(settings.storage.database_url)
    trade_queue = TradeQueue(store=store, ttl_hours=settings.funding_alert.trade_queue_ttl_hours)
    setup_gate = SetupGate(min_trend=-1.0, min_rsi=40.0)
    health_monitor = HealthMonitor(started_at=datetime.utcnow())
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
        ensemble=ensemble,
        risk_manager=risk_manager,
        execution=execution,
        store=store,
        trade_queue=trade_queue,
        setup_gate=setup_gate,
        health_monitor=health_monitor,
        position_manager=position_manager,
    )
    orchestrator.start()
    result = orchestrator.run_cycle(["AAPL"])
    assert result["processed"] == 1
    assert "decisions" in result
