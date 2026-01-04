from __future__ import annotations

from datetime import datetime
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
from src.core.portfolio.snapshot import PortfolioSnapshot
from src.core.risk.manager import RiskManager
from src.core.settings import Settings, load_settings


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "ui" / "templates"
STATIC_DIR = Path(__file__).resolve().parents[1] / "ui" / "static"


def build_test_center(settings: Settings, use_mock: bool = False) -> TestCenterService:
    if use_mock:
        client = MockAlpacaClient()
    else:
        credentials = AlpacaCredentials(
            api_key=settings.alpaca_paper_api_key,
            secret_key=settings.alpaca_paper_secret_key,
            trading_base_url=settings.alpaca.trading_base_url,
            data_base_url=settings.alpaca.data_base_url,
        )
        client = AlpacaClient(credentials, paper=True)
    cache = DataCache(settings.storage.cache_dir)
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


def create_app(settings: Optional[Settings] = None, test_center: Optional[TestCenterService] = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Ultimate Trading Bot v2", version="0.1.0")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    health_monitor = HealthMonitor(started_at=datetime.utcnow())
    test_center = test_center or build_test_center(settings)

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
            },
        )

    @app.get("/api/settings", response_class=JSONResponse)
    def api_settings() -> dict:
        return settings.model_dump()

    @app.get("/api/portfolio", response_class=JSONResponse)
    def portfolio_snapshot() -> dict:
        try:
            account = test_center.execution.client.get_account()
            snapshot = PortfolioSnapshot.from_account(account)
            return snapshot.__dict__
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}

    @app.get("/api/test-center/checks", response_class=JSONResponse)
    def test_center_checks() -> list[TestCenterCheck]:
        return test_center.run_checks()

    return app


app = create_app()


if __name__ == "__main__":
    import webbrowser

    import uvicorn

    settings = load_settings()
    if settings.app.auto_open_browser:
        webbrowser.open(f"http://{settings.app.host}:{settings.app.port}")
    uvicorn.run("src.app.main:app", host=settings.app.host, port=settings.app.port, reload=False)
