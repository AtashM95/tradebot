from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Optional

import requests


@dataclass
class SentimentResult:
    score: float
    source: str
    detail: str
    cached: bool = False


@dataclass
class SentimentProvider:
    provider: str
    newsapi_key: Optional[str]
    finnhub_key: Optional[str]
    cache_ttl_seconds: int = 900

    def __post_init__(self) -> None:
        self._cache: dict[str, tuple[datetime, SentimentResult]] = {}

    def get_sentiment(self, symbol: str) -> SentimentResult:
        now = datetime.now(timezone.utc)
        cached = self._cache.get(symbol)
        if cached and now - cached[0] < timedelta(seconds=self.cache_ttl_seconds):
            result = cached[1]
            return SentimentResult(score=result.score, source=result.source, detail=result.detail, cached=True)

        if self.provider == "finnhub" and self.finnhub_key:
            result = self._finnhub_sentiment(symbol)
        elif self.provider == "newsapi" and self.newsapi_key:
            result = self._newsapi_sentiment(symbol)
        else:
            result = SentimentResult(score=0.0, source="none", detail="No sentiment provider configured.")

        self._cache[symbol] = (now, result)
        return result

    def _finnhub_sentiment(self, symbol: str) -> SentimentResult:
        logger = logging.getLogger(__name__)
        try:
            response = requests.get(
                "https://finnhub.io/api/v1/news-sentiment",
                params={"symbol": symbol, "token": self.finnhub_key},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            score = float(data.get("companyNewsScore", 0.0))
            return SentimentResult(score=score, source="finnhub", detail="Finnhub news sentiment.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Finnhub sentiment failed for %s: %s", symbol, exc)
            return SentimentResult(score=0.0, source="finnhub", detail="Finnhub error.")

    def _newsapi_sentiment(self, symbol: str) -> SentimentResult:
        logger = logging.getLogger(__name__)
        try:
            response = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": symbol,
                    "language": "en",
                    "pageSize": 20,
                    "apiKey": self.newsapi_key,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            titles = [article.get("title", "") for article in data.get("articles", [])]
            score = _score_titles(titles)
            return SentimentResult(score=score, source="newsapi", detail="NewsAPI keyword score.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("NewsAPI sentiment failed for %s: %s", symbol, exc)
            return SentimentResult(score=0.0, source="newsapi", detail="NewsAPI error.")


def _score_titles(titles: list[str]) -> float:
    positive = {"beat", "upgrade", "strong", "growth", "outperform", "record", "profit"}
    negative = {"miss", "downgrade", "weak", "lawsuit", "decline", "drop", "loss"}
    if not titles:
        return 0.0
    score = 0
    for title in titles:
        lowered = title.lower()
        score += sum(word in lowered for word in positive)
        score -= sum(word in lowered for word in negative)
    return float(score) / float(max(len(titles), 1))
