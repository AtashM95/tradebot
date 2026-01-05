from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Optional
import pickle
import re

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd

from src.core.backtest.walk_forward import WalkForwardBacktester
from src.core.contracts import TestCenterCheck
from src.core.data.alpaca_client import AlpacaClient, AlpacaCredentials, MockAlpacaClient
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
from src.core.monitoring.center_service import TestCenterService
from src.core.monitoring.performance import PerformanceMonitor
from src.core.ml.drift import detect_drift
from src.core.ml.registry import ModelRegistry
from src.core.ml.retrain import RetrainPipeline
from src.core.ml.shadow import ShadowTester
from src.core.orchestrator.service import Orchestrator
from src.core.orchestrator.setup_gate import SetupGate
from src.core.sentiment.provider import SentimentProvider
from src.core.portfolio.position_manager import PositionManager
from src.core.portfolio.snapshot import PortfolioSnapshot
from src.core.portfolio.trade_queue import TradeQueue
from src.core.risk.correlation import CorrelationManager
from src.core.risk.manager import RiskManager
from src.core.settings import Settings, load_settings
from src.core.storage.db import SQLiteStore


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "ui" / "templates"
STATIC_DIR = Path(__file__).resolve().parents[1] / "ui" / "static"
I18N_PATH = Path(__file__).resolve().parents[1] / "ui" / "i18n" / "tr.json"


def load_i18n() -> dict:
    return json.loads(I18N_PATH.read_text(encoding="utf-8"))


def _env_mock_mode() -> bool:
    return os.getenv("TRADEBOT_MOCK_MODE", "").strip().lower() in {"1", "true", "yes"}


def load_sector_map(path: str) -> dict:
    sector_path = Path(path)
    if not sector_path.exists():
        raise ValueError(f"Sector map not found: {sector_path}")
    data = json.loads(sector_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("Sector map must be a non-empty object.")
    return {str(symbol).upper(): str(sector) for symbol, sector in data.items()}


def build_clients(settings: Settings, use_mock: bool = False) -> tuple[AlpacaClient | MockAlpacaClient, bool]:
    if use_mock:
        return MockAlpacaClient(), True

    mode = settings.app.mode
    if mode == "live":
        if not settings.alpaca_live_api_key or not settings.alpaca_live_secret_key:
            raise ValueError(
                "LIVE modunda ALPACA_LIVE_API_KEY ve ALPACA_LIVE_SECRET_KEY zorunludur."
            )
        credentials = AlpacaCredentials(
            api_key=settings.alpaca_live_api_key,
            secret_key=settings.alpaca_live_secret_key,
            trading_base_url=settings.alpaca.trading_base_url,
            data_base_url=settings.alpaca.data_base_url,
        )
        return AlpacaClient(credentials, paper=False), False

    if mode == "paper":
        if not settings.alpaca_paper_api_key or not settings.alpaca_paper_secret_key:
            return MockAlpacaClient(), True
        credentials = AlpacaCredentials(
            api_key=settings.alpaca_paper_api_key,
            secret_key=settings.alpaca_paper_secret_key,
            trading_base_url=settings.alpaca.trading_base_url,
            data_base_url=settings.alpaca.data_base_url,
        )
        return AlpacaClient(credentials, paper=True), False

    return MockAlpacaClient(), True


def build_test_center(settings: Settings, use_mock: bool = False) -> TestCenterService:
    client, _ = build_clients(settings, use_mock=use_mock)
    cache = DataCache(settings.storage.cache_dir, compression=settings.storage.data_compression)
    data_provider = MarketDataProvider(client=client, cache=cache)
    feature_engine = FeatureEngine(atr_period=settings.risk.stop_takeprofit.atr_period)
    ensemble = EnsembleAggregator(min_score=settings.ensemble.min_final_score_to_trade)
    risk_manager = RiskManager(
        risk_per_trade=settings.risk.risk_per_trade,
        max_position_weight=settings.risk.max_position_weight,
        cash_buffer=settings.risk.cash_buffer,
    )
    order_manager = OrderManager(client=client, ttl_minutes=settings.order_manager.stale_order_ttl_minutes)
    execution = ExecutionService(settings=settings, client=client, order_manager=order_manager)
    backtester = WalkForwardBacktester(
        data_provider=data_provider,
        feature_engine=feature_engine,
        ensemble=ensemble,
        risk_manager=risk_manager,
        strategy_toggles=settings.strategies,
    )
    return TestCenterService(
        data_provider=data_provider,
        feature_engine=feature_engine,
        ensemble=ensemble,
        risk_manager=risk_manager,
        execution=execution,
        backtester=backtester,
        strategy_toggles=settings.strategies,
    )


def create_app(
    settings: Optional[Settings] = None,
    test_center: Optional[TestCenterService] = None,
    use_mock: Optional[bool] = None,
) -> FastAPI:
    settings = settings or load_settings()
    i18n = load_i18n()
    app = FastAPI(title="Ultimate Trading Bot v2", version="0.1.0")
    app.state.settings = settings
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    health_monitor = HealthMonitor(started_at=datetime.now(timezone.utc))
    effective_mock = _env_mock_mode() if use_mock is None else use_mock
    client, mock_mode = build_clients(settings, use_mock=effective_mock)
    cache = DataCache(settings.storage.cache_dir, compression=settings.storage.data_compression)
    data_provider = MarketDataProvider(client=client, cache=cache)
    feature_engine = FeatureEngine(atr_period=settings.risk.stop_takeprofit.atr_period)
    data_validator = MarketDataValidator()
    ensemble = EnsembleAggregator(min_score=settings.ensemble.min_final_score_to_trade)
    risk_manager = RiskManager(
        risk_per_trade=settings.risk.risk_per_trade,
        max_position_weight=settings.risk.max_position_weight,
        cash_buffer=settings.risk.cash_buffer,
    )
    order_manager = OrderManager(client=client, ttl_minutes=settings.order_manager.stale_order_ttl_minutes)
    execution = ExecutionService(settings=settings, client=client, order_manager=order_manager)
    slippage_model = SlippageModel(
        spread_bps=settings.slippage.spread_bps,
        fee_bps=settings.slippage.fee_bps,
    )
    circuit_breaker = CircuitBreaker(
        max_failures=settings.circuit_breaker.max_failures,
        drawdown_limit=settings.circuit_breaker.drawdown_limit,
        cooldown_minutes=settings.circuit_breaker.cooldown_minutes,
    )
    error_handler = ErrorHandler(
        max_retries=settings.error_handling.max_retries,
        retry_delay_seconds=settings.error_handling.retry_delay_seconds,
    )
    performance_monitor = PerformanceMonitor()
    alert_manager = AlertManager(
        cooldown_seconds=settings.alerts.alert_cooldown_seconds,
        telegram_token=settings.alerts.telegram_token,
        telegram_chat_id=settings.alerts.telegram_chat_id,
    )
    correlation_manager = CorrelationManager(
        max_symbol_correlation=settings.risk.max_symbol_correlation,
        max_sector_weight=settings.risk.max_sector_weight,
    )
    sentiment_provider = SentimentProvider(
        provider=settings.sentiment.provider,
        newsapi_key=settings.newsapi_key,
        finnhub_key=settings.finnhub_key,
        cache_ttl_seconds=settings.sentiment.cache_ttl_seconds,
    )
    sector_map = load_sector_map(settings.sector_map_path)
    store = SQLiteStore(settings.storage.database_url)
    store.seed_watchlist(settings.universe.watchlist_default)
    trade_queue = TradeQueue(store=store, ttl_hours=settings.funding_alert.trade_queue_ttl_hours)
    setup_gate = SetupGate(
        min_trend=settings.setup_gate.min_trend,
        min_rsi=settings.setup_gate.min_rsi,
    )
    position_manager = PositionManager(
        data_provider=data_provider,
        feature_engine=feature_engine,
        execution=execution,
        performance_monitor=performance_monitor,
        store=store,
        max_hold_days=settings.trading.target_hold_days_max,
        trailing_stop_enabled=settings.risk.stop_takeprofit.trailing_stop_enabled,
        trailing_atr_multiplier=settings.risk.stop_takeprofit.trailing_atr_multiplier,
    )
    backtester = WalkForwardBacktester(
        data_provider=data_provider,
        feature_engine=feature_engine,
        ensemble=ensemble,
        risk_manager=risk_manager,
        strategy_toggles=settings.strategies,
        train_days=settings.ml.validation.train_window_days,
        test_days=settings.ml.validation.test_window_days,
        step_days=settings.ml.validation.step_window_days,
    )
    orchestrator = Orchestrator(
        settings=settings,
        data_provider=data_provider,
        feature_engine=feature_engine,
        data_validator=data_validator,
        ensemble=ensemble,
        risk_manager=risk_manager,
        correlation_manager=correlation_manager,
        sector_map=sector_map,
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
        sentiment_provider=sentiment_provider,
        position_manager=position_manager,
    )
    test_center = test_center or build_test_center(settings, use_mock=mock_mode)

    @app.get("/health", response_class=JSONResponse)
    def health() -> dict:
        return health_monitor.status()

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request):
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "mode": settings.app.mode,
                "watchlist": store.get_watchlist(),
                "risk": settings.risk.model_dump(),
                "mock_mode": mock_mode,
                "i18n": i18n,
            },
        )

    @app.get("/api/settings", response_class=JSONResponse)
    def api_settings() -> dict:
        return settings.model_dump()

    @app.get("/api/status", response_class=JSONResponse)
    def api_status() -> dict:
        return {
            "mode": settings.app.mode,
            "mock_mode": mock_mode,
            "orchestrator_status": orchestrator.status,
            "last_run": orchestrator.last_run_summary,
        }

    @app.get("/api/portfolio", response_class=JSONResponse)
    def portfolio_snapshot() -> dict:
        try:
            account = orchestrator.execution.client.get_account()
            snapshot = PortfolioSnapshot.from_account(account)
            positions = orchestrator.execution.client.list_positions()
            return {**snapshot.__dict__, "positions": positions}
        except Exception as exc:  # noqa: BLE001
            store.add_log("error", f"Portföy alınamadı: {exc}")
            return {"error": "Portföy bilgisi alınamadı."}

    @app.get("/api/test-center/checks", response_class=JSONResponse)
    def test_center_checks() -> list[TestCenterCheck]:
        checks = test_center.run_checks()
        if mock_mode:
            for check in checks:
                check.details["mock_mode"] = "true"
        return checks

    @app.post("/api/orchestrator/start", response_class=JSONResponse)
    def start_orchestrator() -> dict:
        orchestrator.start()
        return {"status": orchestrator.status}

    @app.post("/api/orchestrator/pause", response_class=JSONResponse)
    def pause_orchestrator() -> dict:
        orchestrator.pause()
        return {"status": orchestrator.status}

    @app.post("/api/orchestrator/stop", response_class=JSONResponse)
    def stop_orchestrator() -> dict:
        orchestrator.stop()
        return {"status": orchestrator.status}

    @app.post("/api/live/unlock", response_class=JSONResponse)
    async def unlock_live(request: Request) -> dict:
        payload = await request.json()
        live_checkbox = bool(payload.get("live_checkbox", False))
        provided_pin = payload.get("pin")
        provided_phrase = payload.get("phrase")
        try:
            expires = execution.unlock_live_session(
                live_checkbox=live_checkbox,
                provided_pin=provided_pin,
                provided_phrase=provided_phrase,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "status": "unlocked",
            "expires_at": expires.isoformat(),
            "active": execution._session_active(),
        }

    @app.get("/api/watchlist", response_class=JSONResponse)
    def get_watchlist() -> dict:
        return {"symbols": store.get_watchlist()}

    @app.post("/api/watchlist", response_class=JSONResponse)
    def update_watchlist(payload: dict) -> dict:
        symbols = payload.get("symbols")
        if isinstance(symbols, str):
            raw = symbols.replace(",", " ").split()
            symbols = [symbol.strip().upper() for symbol in raw if symbol.strip()]
        if not isinstance(symbols, list):
            return {"error": "Semboller liste veya metin olmalıdır."}
        cleaned = []
        invalid = []
        for symbol in symbols:
            if not isinstance(symbol, str):
                invalid.append(str(symbol))
                continue
            symbol = symbol.strip().upper()
            if not re.match(r"^[A-Z0-9][A-Z0-9.-]{0,9}$", symbol):
                invalid.append(symbol)
                continue
            cleaned.append(symbol)
        cleaned = list(dict.fromkeys(cleaned))
        if invalid:
            return {"error": f"Geçersiz semboller: {', '.join(invalid)}"}
        if not 1 <= len(cleaned) <= settings.universe.watchlist_max_size:
            return {"error": "İzleme listesi 1 ile 200 sembol arasında olmalıdır."}
        if len(cleaned) < 100:
            store.add_log("warning", "İzleme listesi çeşitlendirme için önerilen 100 sembolün altında.")
        store.set_watchlist(cleaned)
        return {"symbols": cleaned}

    @app.post("/api/analyze", response_class=JSONResponse)
    def analyze(payload: dict) -> dict:
        symbols = payload.get("symbols")
        if not isinstance(symbols, list):
            return {"error": "Semboller liste olmalıdır."}
        return orchestrator.run_cycle(symbols)

    @app.post("/api/run-cycle", response_class=JSONResponse)
    def run_cycle(payload: dict) -> dict:
        symbols = payload.get("symbols")
        if not isinstance(symbols, list):
            return {"error": "Semboller liste olmalıdır."}
        return orchestrator.run_cycle(symbols)

    @app.post("/api/analyze/all", response_class=JSONResponse)
    def analyze_all() -> dict:
        symbols = store.get_watchlist()
        return orchestrator.run_cycle(symbols)

    @app.post("/api/backtest/run", response_class=JSONResponse)
    async def run_backtest(request: Request) -> dict:
        payload = await request.json()
        symbols = payload.get("symbols") or store.get_watchlist()
        if isinstance(symbols, str):
            symbols = [s.strip().upper() for s in symbols.replace(",", " ").split() if s.strip()]
        if not isinstance(symbols, list) or not symbols:
            raise HTTPException(status_code=400, detail="Symbols must be a non-empty list.")
        years = int(payload.get("years", settings.ml.validation.backtest_years))
        train_days = int(payload.get("train_days", settings.ml.validation.train_window_days))
        test_days = int(payload.get("test_days", settings.ml.validation.test_window_days))
        step_days = int(payload.get("step_days", settings.ml.validation.step_window_days))
        backtester.train_days = train_days
        backtester.test_days = test_days
        backtester.step_days = step_days
        report = backtester.run(symbols, years=years)
        equity_curve = []
        for fold in report.get("folds", []):
            equity_curve.extend(fold.get("equity_curve", []))
        return {
            "summary": report.get("summary", ""),
            "aggregate": report.get("aggregate", {}),
            "equity_curve": equity_curve,
            "folds": len(report.get("folds", [])),
        }

    @app.get("/api/models/list", response_class=JSONResponse)
    def list_models() -> list[dict]:
        registry = ModelRegistry(base_dir=Path(settings.ml.registry.directory))
        return registry.list_models()

    @app.get("/api/models/active", response_class=JSONResponse)
    def active_model() -> dict:
        registry = ModelRegistry(base_dir=Path(settings.ml.registry.directory))
        active = registry.get_active_model()
        return active or {}

    @app.post("/api/models/set-active", response_class=JSONResponse)
    async def set_active_model(request: Request) -> dict:
        payload = await request.json()
        model_id = payload.get("model_id")
        if not model_id:
            raise HTTPException(status_code=400, detail="model_id is required.")
        registry = ModelRegistry(base_dir=Path(settings.ml.registry.directory))
        try:
            registry.set_active_model(model_id)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "ok", "active_model": model_id}

    @app.post("/api/models/drift-check", response_class=JSONResponse)
    async def drift_check(request: Request) -> dict:
        payload = await request.json()
        baseline = payload.get("baseline")
        current = payload.get("current")
        if not isinstance(baseline, list) or not isinstance(current, list):
            raise HTTPException(status_code=400, detail="baseline and current must be list of records.")
        baseline_df = pd.DataFrame(baseline)
        current_df = pd.DataFrame(current)
        report = detect_drift(baseline_df, current_df, alpha=float(payload.get("alpha", 0.05)))
        return report.model_dump()

    @app.post("/api/models/shadow-test", response_class=JSONResponse)
    async def shadow_test(request: Request) -> dict:
        payload = await request.json()
        candidate_id = payload.get("candidate_model_id")
        active_id = payload.get("active_model_id")
        features = payload.get("features")
        target = payload.get("target")
        if not candidate_id or not isinstance(features, list) or not isinstance(target, list):
            raise HTTPException(status_code=400, detail="candidate_model_id, features, and target are required.")
        registry = ModelRegistry(base_dir=Path(settings.ml.registry.directory))
        models = {model["model_id"]: model for model in registry.list_models()}
        candidate_entry = models.get(candidate_id)
        active_entry = models.get(active_id) if active_id else registry.get_active_model()
        if not candidate_entry or not active_entry:
            raise HTTPException(status_code=400, detail="Candidate or active model not found.")
        candidate_model = pickle.load(Path(candidate_entry["artifact_path"]).open("rb"))
        active_model = pickle.load(Path(active_entry["artifact_path"]).open("rb"))
        tester = ShadowTester(days=settings.ml.shadow_test.days)
        features_arr = pd.DataFrame(features).to_numpy()
        target_arr = pd.Series(target).to_numpy()
        result = tester.run(candidate_model, active_model, features_arr, target_arr)
        return result.__dict__

    @app.post("/api/models/retrain", response_class=JSONResponse)
    async def retrain_model(request: Request) -> dict:
        payload = await request.json()
        features = payload.get("features")
        target = payload.get("target")
        if not isinstance(features, list) or not isinstance(target, list):
            raise HTTPException(status_code=400, detail="features and target are required lists.")
        algorithm = payload.get("algorithm", "logistic_regression")
        features_df = pd.DataFrame(features)
        target_series = pd.Series(target)
        pipeline = RetrainPipeline(schedule=settings.ml.retrain_schedule)
        result = pipeline.run(
            features=features_df,
            target=target_series,
            registry_dir=settings.ml.registry.directory,
            feature_list=list(features_df.columns),
            algorithm=algorithm,
        )
        return result.__dict__

    @app.get("/api/funding-alerts", response_class=JSONResponse)
    def funding_alerts() -> list[dict]:
        rows = store.list_funding_alerts(limit=50)
        return [
            {
                "id": row["id"],
                "symbol": row["symbol"],
                "missing_cash": row["missing_cash"],
                "proposed_actions": row["proposed_actions"],
                "details": row["details"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    @app.get("/api/logs", response_class=JSONResponse)
    def logs(limit: int = 50) -> list[dict]:
        rows = store.list_logs(limit=limit)
        return [
            {
                "id": row["id"],
                "level": row["level"],
                "message": row["message"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    return app


app = create_app(use_mock=_env_mock_mode())


if __name__ == "__main__":
    import webbrowser

    import uvicorn

    settings = load_settings()
    if settings.app.auto_open_browser:
        webbrowser.open(f"http://{settings.app.host}:{settings.app.port}")
    uvicorn.run("src.app.main:app", host=settings.app.host, port=settings.app.port, reload=False)
