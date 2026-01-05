from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Optional

from src.core.settings import Settings
from src.integrations.openai_client import call_structured
from src.integrations.openai_schemas import (
    DailyOpsReport,
    NewsRiskGateResult,
    TradeExplanation,
    schema_for,
)


class TTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[float, dict]] = {}

    def get(self, key: str) -> Optional[dict]:
        entry = self._store.get(key)
        if not entry:
            return None
        created_at, payload = entry
        if time.time() - created_at > self.ttl_seconds:
            self._store.pop(key, None)
            return None
        return payload

    def set(self, key: str, payload: dict) -> None:
        self._store[key] = (time.time(), payload)


def _hash_payload(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass
class NewsRiskGateService:
    settings: Settings
    cache: TTLCache = field(init=False)

    def __post_init__(self) -> None:
        self.cache = TTLCache(self.settings.openai_cache_ttl_seconds)

    def evaluate(
        self,
        ticker: str,
        headlines: list[str],
        earnings_date: Optional[str],
        last_price: float,
        volatility_proxy: float,
    ) -> NewsRiskGateResult:
        if not self.settings.openai_enabled or self.settings.openai_news_gate_mode == "off":
            return NewsRiskGateResult(risk_flag="LOW", trade_allowed=True, reasons=[], confidence=0.0)
        payload = {
            "ticker": ticker,
            "headlines": headlines,
            "earnings_date": earnings_date,
            "last_price": last_price,
            "volatility_proxy": volatility_proxy,
        }
        cache_key = _hash_payload(payload)
        cached = self.cache.get(cache_key)
        if cached:
            return NewsRiskGateResult.model_validate(cached)
        result = call_structured(
            schema=schema_for(NewsRiskGateResult),
            instructions=(
                "You are a risk gate. Only return the JSON schema. "
                "Assess news/earnings risk. If risk is high, set trade_allowed=false."
            ),
            input=payload,
            tags=["news-risk-gate"],
            timeout=self.settings.openai_timeout_seconds,
            retries=self.settings.openai_max_retries,
        )
        if not result:
            return NewsRiskGateResult(risk_flag="LOW", trade_allowed=True, reasons=[], confidence=0.0)
        validated = NewsRiskGateResult.model_validate(result)
        self.cache.set(cache_key, validated.model_dump())
        return validated


@dataclass
class TradeExplainerService:
    settings: Settings
    cache: TTLCache = field(init=False)

    def __post_init__(self) -> None:
        self.cache = TTLCache(self.settings.openai_cache_ttl_seconds)

    def explain(
        self,
        signal_intent: dict,
        setup_gate: dict,
        indicators_snapshot: dict,
        risk_decision: dict,
    ) -> TradeExplanation:
        if not self.settings.openai_enabled:
            return TradeExplanation(decision="ALLOW", bullets=["OpenAI disabled"], key_factors=[])
        payload = {
            "signal_intent": signal_intent,
            "setup_gate": setup_gate,
            "indicators_snapshot": indicators_snapshot,
            "risk_decision": risk_decision,
        }
        cache_key = _hash_payload(payload)
        cached = self.cache.get(cache_key)
        if cached:
            return TradeExplanation.model_validate(cached)
        result = call_structured(
            schema=schema_for(TradeExplanation),
            instructions=(
                "You are a trade explainer. Only return the JSON schema. "
                "Explain the decision with concise bullets and key factors."
            ),
            input=payload,
            tags=["trade-explainer"],
            timeout=self.settings.openai_timeout_seconds,
            retries=self.settings.openai_max_retries,
        )
        if not result:
            return TradeExplanation(decision="ALLOW", bullets=["Explanation unavailable"], key_factors=[])
        validated = TradeExplanation.model_validate(result)
        self.cache.set(cache_key, validated.model_dump())
        return validated


@dataclass
class DailyOpsReporterService:
    settings: Settings
    cache: TTLCache = field(init=False)

    def __post_init__(self) -> None:
        self.cache = TTLCache(self.settings.openai_cache_ttl_seconds)

    def report(self, metrics: dict) -> DailyOpsReport:
        if not self.settings.openai_enabled:
            return DailyOpsReport(summary="OpenAI disabled", pnl_today=None, drawdown=None, incidents=[])
        cache_key = _hash_payload(metrics)
        cached = self.cache.get(cache_key)
        if cached:
            return DailyOpsReport.model_validate(cached)
        result = call_structured(
            schema=schema_for(DailyOpsReport),
            instructions=(
                "You are an ops reporter. Only return the JSON schema. "
                "Summarize daily trading operations and incidents."
            ),
            input=metrics,
            tags=["daily-ops-report"],
            timeout=self.settings.openai_timeout_seconds,
            retries=self.settings.openai_max_retries,
        )
        if not result:
            return DailyOpsReport(summary="Report unavailable", pnl_today=None, drawdown=None, incidents=[])
        validated = DailyOpsReport.model_validate(result)
        self.cache.set(cache_key, validated.model_dump())
        return validated
