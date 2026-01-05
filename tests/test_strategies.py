from datetime import datetime, timezone

from src.core.contracts import Features
from src.core.strategies.strategies import build_strategies


def test_strategies_generate_signal():
    features = Features(
        symbol="AAPL",
        computed_at=datetime.now(timezone.utc),
        values={
            "close": 150.0,
            "atr": 2.0,
            "rsi": 60.0,
            "ema_fast": 151.0,
            "ema_slow": 149.0,
            "trend": 2.0,
            "vol_avg": 1_000_000.0,
        },
    )
    intents = [strategy.generate(features) for strategy in build_strategies()]
    assert any(intent is not None for intent in intents)
