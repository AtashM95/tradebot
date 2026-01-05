from __future__ import annotations

from pathlib import Path
import os
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


Mode = Literal["backtest", "paper", "live"]


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config YAML must be a mapping/object. Got: {type(data)}")
    return data


class AppSettings(BaseModel):
    mode: Mode = "paper"
    host: str = "127.0.0.1"
    port: int = 5000
    auto_open_browser: bool = True
    log_level: str = "INFO"
    cycle_interval_seconds: int = 600


class StorageSettings(BaseModel):
    database_url: str = "sqlite:///data/trading_bot.db"
    data_dir: str = "data"
    cache_dir: str = "data/cache"
    models_dir: str = "models"
    logs_dir: str = "logs"
    data_cache_format: str = "parquet"
    data_compression: str = "zstd"
    data_cache_keep_bars: int = 300


class AlpacaSettings(BaseModel):
    trading_base_url: str = ""  # optional override
    data_base_url: str = ""     # optional override
    paper_default: bool = True


class UniverseSettings(BaseModel):
    watchlist_default: List[str] = Field(default_factory=lambda: ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"])
    watchlist_max_size: int = 200


class TradingConstraints(BaseModel):
    long_only: bool = True
    allow_short: bool = False
    allow_options: bool = False
    allow_crypto: bool = False
    allow_fx: bool = False
    target_hold_days_min: int = 5
    target_hold_days_max: int = 14
    trade_only_market_hours: bool = True


class StopTakeProfit(BaseModel):
    stop_method: Literal["atr", "fixed", "structure"] = "atr"
    atr_period: int = 14
    atr_multiplier_stop: float = 2.0
    atr_multiplier_tp: float = 4.0
    trailing_stop_enabled: bool = True
    trailing_atr_multiplier: float = 2.5


class RebalanceSettings(BaseModel):
    frequency: Literal["weekly", "manual"] = "weekly"
    threshold: float = 0.06


class RiskSettings(BaseModel):
    profile: Literal["conservative", "balanced", "aggressive"] = "balanced"
    risk_per_trade: float = 0.005
    max_open_positions: int = 10
    max_position_weight: float = 0.12
    max_sector_weight: float = 0.30
    max_symbol_correlation: float = 0.85
    cash_buffer: float = 0.08
    daily_max_loss: float = 0.02
    weekly_max_drawdown: float = 0.05
    stop_takeprofit: StopTakeProfit = Field(default_factory=StopTakeProfit)
    rebalance: RebalanceSettings = Field(default_factory=RebalanceSettings)


class FundingAlertSettings(BaseModel):
    enabled: bool = True
    swap_score_gap_threshold: float = 0.15
    partial_entry_enabled: bool = True
    partial_entry_fraction: float = 0.25
    trade_queue_enabled: bool = True
    trade_queue_ttl_hours: int = 48
    desktop_notifications: bool = True


class StrategyToggles(BaseModel):
    enable_setup_gate: bool = True
    enable_trend_following: bool = True
    enable_breakout: bool = True
    enable_pullback_retest: bool = True
    enable_rsi_momentum: bool = True
    enable_candle_patterns: bool = True
    enable_fib_pullback: bool = True
    enable_volume_confirm: bool = True


class EnsembleSettings(BaseModel):
    method: Literal["weighted", "majority", "stacking"] = "weighted"
    min_final_score_to_trade: float = 0.70


class SentimentSettings(BaseModel):
    enabled: bool = True
    provider: Literal["finnhub", "newsapi"] = "finnhub"
    min_score: float = -0.2
    cache_ttl_seconds: int = 900


class SetupGateSettings(BaseModel):
    min_trend: float = 0.0
    min_rsi: float = 45.0


class MLValidationSettings(BaseModel):
    backtest_years: int = 5
    walk_forward_enabled: bool = True
    train_window_days: int = 504
    test_window_days: int = 126
    step_window_days: int = 63


class MLDriftThresholds(BaseModel):
    data_drift_threshold: float = 0.15
    performance_drift_threshold: float = 0.10


class MLHPOSettings(BaseModel):
    enabled: bool = True
    engine: Literal["optuna"] = "optuna"
    trials: int = 50


class MLShadowTestSettings(BaseModel):
    on_paper: bool = True
    days: int = 3


class MLRegistrySettings(BaseModel):
    enabled: bool = True
    promotion_policy: Literal["paper_pass_then_manual"] = "paper_pass_then_manual"
    directory: str = "models/registry"


class MLSettings(BaseModel):
    enabled: bool = True
    retrain_schedule: Literal["weekly", "manual"] = "weekly"
    retrain_on_drift: bool = True
    retrain_on_performance_drop: bool = True
    validation: MLValidationSettings = Field(default_factory=MLValidationSettings)
    drift_thresholds: MLDriftThresholds = Field(default_factory=MLDriftThresholds)
    hpo: MLHPOSettings = Field(default_factory=MLHPOSettings)
    shadow_test: MLShadowTestSettings = Field(default_factory=MLShadowTestSettings)
    registry: MLRegistrySettings = Field(default_factory=MLRegistrySettings)


class LiveSafetySettings(BaseModel):
    lock_enabled: bool = True
    confirm_phrase: str = "I_UNDERSTAND_LIVE_TRADING_RISK"
    session_minutes: int = 15


class CircuitBreakerSettings(BaseModel):
    max_failures: int = 3
    drawdown_limit: float = 0.15
    cooldown_minutes: int = 30


class ErrorHandlingSettings(BaseModel):
    max_retries: int = 2
    retry_delay_seconds: int = 2


class OrderManagerSettings(BaseModel):
    stale_order_ttl_minutes: int = 10


class SlippageSettings(BaseModel):
    spread_bps: float = 2.0
    fee_bps: float = 1.0


class AlertSettings(BaseModel):
    alert_cooldown_seconds: int = 300
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    consecutive_losses_limit: int = 3
    low_cash_threshold: float = 0.05


class Settings(BaseSettings):
    """
    Precedence:
      - OS env vars always override dotenv and YAML. 3
      - dotenv (.env) is loaded by pydantic-settings via model_config env_file.
      - YAML is provided as init kwargs (lowest priority among these).
    """

    # ---- Structured settings (from YAML defaults) ----
    app: AppSettings = Field(default_factory=AppSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    alpaca: AlpacaSettings = Field(default_factory=AlpacaSettings)
    universe: UniverseSettings = Field(default_factory=UniverseSettings)
    trading: TradingConstraints = Field(default_factory=TradingConstraints)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    funding_alert: FundingAlertSettings = Field(default_factory=FundingAlertSettings)
    strategies: StrategyToggles = Field(default_factory=StrategyToggles)
    ensemble: EnsembleSettings = Field(default_factory=EnsembleSettings)
    sentiment: SentimentSettings = Field(default_factory=SentimentSettings)
    setup_gate: SetupGateSettings = Field(default_factory=SetupGateSettings)
    ml: MLSettings = Field(default_factory=MLSettings)
    live_safety: LiveSafetySettings = Field(default_factory=LiveSafetySettings)
    notifications_enabled: bool = True
    circuit_breaker: CircuitBreakerSettings = Field(default_factory=CircuitBreakerSettings)
    error_handling: ErrorHandlingSettings = Field(default_factory=ErrorHandlingSettings)
    order_manager: OrderManagerSettings = Field(default_factory=OrderManagerSettings)
    slippage: SlippageSettings = Field(default_factory=SlippageSettings)
    alerts: AlertSettings = Field(default_factory=AlertSettings)
    sector_map_path: str = "config/sector_map.json"

    # ---- Secrets / keys (from ENV/.env) ----
    alpaca_paper_api_key: Optional[str] = None
    alpaca_paper_secret_key: Optional[str] = None
    alpaca_live_api_key: Optional[str] = None
    alpaca_live_secret_key: Optional[str] = None

    newsapi_key: Optional[str] = None
    finnhub_key: Optional[str] = None
    fred_api_key: Optional[str] = None

    openai_api_key: Optional[str] = None
    openai_enabled: bool = False
    openai_model: str = "gpt-5"
    openai_timeout_seconds: int = 30
    openai_max_retries: int = 5
    openai_temperature: float = 0.2
    openai_cache_ttl_seconds: int = 1800
    openai_news_gate_mode: Literal["off", "veto", "reduce"] = "off"
    openai_news_gate_reduce_factor: float = 0.5

    # Live unlock pin read from ENV/.env only
    live_unlock_pin: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # dotenv/YAML’de fazladan alan olsa bile patlamasın
    )


def load_settings(config_path: str = "config/config.yaml") -> Settings:
    """
    Load YAML defaults, then let pydantic-settings apply dotenv + OS env overrides.
    Env vars will always take priority over dotenv, and dotenv/env override YAML. 4
    """
    cfg = _read_yaml(Path(config_path))
    _apply_backward_compat(cfg)
    # YAML -> Settings kwargs (lowest priority)
    settings = Settings(**cfg)
    env_mode = os.getenv("APP_MODE")
    if env_mode:
        normalized = env_mode.strip().lower()
        if normalized in {"backtest", "paper", "live"}:
            settings.app.mode = normalized  # type: ignore[assignment]
        else:
            raise ValueError(f"Invalid APP_MODE value: {env_mode}")
    validate_settings(settings)
    return settings


def _apply_backward_compat(cfg: Dict[str, Any]) -> None:
    ml_cfg = cfg.get("ml")
    if not isinstance(ml_cfg, dict):
        return
    retrain_cfg = ml_cfg.pop("retrain", None)
    if isinstance(retrain_cfg, dict):
        ml_cfg.setdefault("retrain_schedule", retrain_cfg.get("schedule", ml_cfg.get("retrain_schedule", "weekly")))
        ml_cfg.setdefault("retrain_on_drift", retrain_cfg.get("on_drift", ml_cfg.get("retrain_on_drift", True)))
        ml_cfg.setdefault(
            "retrain_on_performance_drop",
            retrain_cfg.get("on_performance_drop", ml_cfg.get("retrain_on_performance_drop", True)),
        )


class LiveLockError(RuntimeError):
    pass


def validate_settings(settings: Settings) -> None:
    if settings.app.mode == "live" and settings.live_safety.lock_enabled:
        if not settings.live_unlock_pin:
            raise ValueError("LIVE mode requires LIVE_UNLOCK_PIN in env/.env.")
    if settings.risk.max_open_positions <= 0:
        raise ValueError("MAX_OPEN_POSITIONS must be positive.")
    if not 0 < settings.risk.max_position_weight <= 1:
        raise ValueError("MAX_POSITION_WEIGHT must be between 0 and 1.")
    if not 0 < settings.risk.max_sector_weight <= 1:
        raise ValueError("MAX_SECTOR_WEIGHT must be between 0 and 1.")
    if settings.circuit_breaker.max_failures < 1:
        raise ValueError("Circuit breaker max_failures must be >= 1.")
    if settings.circuit_breaker.drawdown_limit <= 0:
        raise ValueError("Circuit breaker drawdown_limit must be positive.")
    if not 0 < settings.openai_news_gate_reduce_factor <= 1:
        raise ValueError("OPENAI_NEWS_GATE_REDUCE_FACTOR must be between 0 and 1.")


def enforce_live_lock(
    settings: Settings,
    live_checkbox: bool,
    provided_pin: Optional[str],
    provided_phrase: Optional[str],
) -> None:
    """
    Enforce LIVE mode safety:
    - checkbox must be true
    - PIN must match settings.live_unlock_pin (from ENV/.env)
    - phrase must match settings.live_safety.confirm_phrase
    """
    if not settings.live_safety.lock_enabled:
        return

    if not live_checkbox:
        raise LiveLockError("LIVE kilidi: UI checkbox onaylanmadı.")

    if not settings.live_unlock_pin:
        raise LiveLockError("LIVE kilidi: LIVE_UNLOCK_PIN env/.env içinde ayarlı değil.")

    if not provided_pin or provided_pin.strip() != settings.live_unlock_pin.strip():
        raise LiveLockError("LIVE kilidi: PIN doğrulanamadı.")

    if settings.live_safety.confirm_phrase:
        if (provided_phrase or "").strip() != settings.live_safety.confirm_phrase.strip():
            raise LiveLockError("LIVE kilidi: Onay cümlesi doğrulanamadı.")
