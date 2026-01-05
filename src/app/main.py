from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.core.backtest.walk_forward import WalkForwardBacktester
from src.core.contracts import TestCenterCheck
from src.core.data.alpaca_client import AlpacaClient, AlpacaCredentials, MockAlpacaClient
from src.core.data.cache import DataCache
from src.core.data.market_data import MarketDataProvider
from src.core.ensemble.aggregator import EnsembleAggregator
from src.core.execution.execution_service import ExecutionService
from src.core.features.feature_engine import FeatureEngine
from src.core.monitoring.health import HealthMonitor
from src.core.monitoring.center_service import TestCenterService
from src.core.orchestrator.service import Orchestrator
from src.core.orchestrator.setup_gate import SetupGate
from src.core.portfolio.position_manager import PositionManager
from src.core.portfolio.snapshot import PortfolioSnapshot
from src.core.portfolio.trade_queue import TradeQueue
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
    execution = ExecutionService(settings=settings, client=client)
    backtester = WalkForwardBacktester()
    return TestCenterService(
        data_provider=data_provider,
        feature_engine=feature_engine,
        ensemble=ensemble,
        risk_manager=risk_manager,
        execution=execution,
        backtester=backtester,
    )


def create_app(
    settings: Optional[Settings] = None,
    test_center: Optional[TestCenterService] = None,
    use_mock: Optional[bool] = None,
) -> FastAPI:
    settings = settings or load_settings()
    i18n = load_i18n()
    app = FastAPI(title="Ultimate Trading Bot v2", version="0.1.0")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    health_monitor = HealthMonitor(started_at=datetime.utcnow())
    effective_mock = _env_mock_mode() if use_mock is None else use_mock
    client, mock_mode = build_clients(settings, use_mock=effective_mock)
    cache = DataCache(settings.storage.cache_dir, compression=settings.storage.data_compression)
    data_provider = MarketDataProvider(client=client, cache=cache)
    feature_engine = FeatureEngine(atr_period=settings.risk.stop_takeprofit.atr_period)
    ensemble = EnsembleAggregator(min_score=settings.ensemble.min_final_score_to_trade)
    risk_manager = RiskManager(
        risk_per_trade=settings.risk.risk_per_trade,
        max_position_weight=settings.risk.max_position_weight,
        cash_buffer=settings.risk.cash_buffer,
    )
    execution = ExecutionService(settings=settings, client=client)
    store = SQLiteStore(settings.storage.database_url)
    store.seed_watchlist(settings.universe.watchlist_default)
    trade_queue = TradeQueue(store=store, ttl_hours=settings.funding_alert.trade_queue_ttl_hours)
    setup_gate = SetupGate()
    position_manager = PositionManager(
        data_provider=data_provider,
        feature_engine=feature_engine,
        execution=execution,
        store=store,
        max_hold_days=settings.trading.target_hold_days_max,
        trailing_stop_enabled=settings.risk.stop_takeprofit.trailing_stop_enabled,
        trailing_atr_multiplier=settings.risk.stop_takeprofit.trailing_atr_multiplier,
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
    test_center = test_center or build_test_center(settings, use_mock=mock_mode)

    @app.get("/health", response_class=JSONResponse)
    def health() -> dict:
        return health_monitor.status()

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request):
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "mode": settings.app.mode,
                "watchlist": settings.universe.watchlist_default,
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
        for symbol in symbols:
            if not symbol.isalpha() or len(symbol) > 5:
                continue
            cleaned.append(symbol.upper())
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

    @app.post("/api/analyze/all", response_class=JSONResponse)
    def analyze_all() -> dict:
        symbols = store.get_watchlist()
        return orchestrator.run_cycle(symbols)

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
