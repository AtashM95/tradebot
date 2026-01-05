from datetime import datetime, timezone

from src.core.contracts import Features
from src.core.strategies.strategies import (
    CandlePatternStrategy,
    FibonacciPullbackStrategy,
    build_strategies,
)


def _base_values() -> dict:
    return {
        "open": 100.0,
        "high": 110.0,
        "low": 95.0,
        "close": 108.0,
        "volume": 1_200_000.0,
        "prev_open": 105.0,
        "prev_high": 106.0,
        "prev_low": 96.0,
        "prev_close": 98.0,
        "prev_volume": 900_000.0,
        "prev2_open": 110.0,
        "prev2_high": 112.0,
        "prev2_low": 100.0,
        "prev2_close": 102.0,
        "prev2_volume": 850_000.0,
        "atr": 2.0,
        "rsi": 60.0,
        "ema_fast": 151.0,
        "ema_slow": 149.0,
        "trend": 2.0,
        "vol_avg": 1_000_000.0,
        "swing_high_50": 120.0,
        "swing_low_50": 90.0,
    }


def test_strategies_generate_signal():
    features = Features(symbol="AAPL", computed_at=datetime.now(timezone.utc), values=_base_values())
    intents = [strategy.generate(features) for strategy in build_strategies()]
    assert any(intent is not None for intent in intents)


def test_candle_pattern_bullish_engulfing():
    values = _base_values()
    values.update(
        {
            "open": 94.0,
            "close": 103.0,
            "high": 104.0,
            "low": 92.0,
            "prev_open": 102.0,
            "prev_close": 95.0,
            "prev_high": 103.0,
            "prev_low": 94.0,
            "trend": -1.0,
        }
    )
    features = Features(symbol="AAPL", computed_at=datetime.now(timezone.utc), values=values)
    signal = CandlePatternStrategy().generate(features)
    assert signal is not None
    assert signal.confidence > 0.6
    assert "Bullish engulfing" in " ".join(signal.reasons)


def test_candle_pattern_hammer():
    values = _base_values()
    values.update(
        {
            "open": 100.0,
            "close": 101.0,
            "high": 102.0,
            "low": 94.0,
            "prev_open": 103.0,
            "prev_close": 96.0,
            "prev_high": 104.0,
            "prev_low": 95.0,
            "trend": -2.0,
        }
    )
    features = Features(symbol="AAPL", computed_at=datetime.now(timezone.utc), values=values)
    signal = CandlePatternStrategy().generate(features)
    assert signal is not None
    assert signal.confidence > 0.6
    assert "Hammer" in " ".join(signal.reasons)


def test_candle_pattern_morning_star():
    values = _base_values()
    values.update(
        {
            "prev2_open": 110.0,
            "prev2_close": 100.0,
            "prev2_high": 111.0,
            "prev2_low": 98.0,
            "prev_open": 101.0,
            "prev_close": 100.9,
            "prev_high": 101.2,
            "prev_low": 100.6,
            "open": 101.0,
            "close": 106.0,
            "high": 107.0,
            "low": 100.0,
            "trend": -1.5,
        }
    )
    features = Features(symbol="AAPL", computed_at=datetime.now(timezone.utc), values=values)
    signal = CandlePatternStrategy().generate(features)
    assert signal is not None
    assert signal.confidence > 0.6
    assert "Morning star" in " ".join(signal.reasons)


def test_fibonacci_pullback_signal():
    values = _base_values()
    swing_high = 120.0
    swing_low = 100.0
    fib_level = swing_high - (swing_high - swing_low) * 0.5
    values.update(
        {
            "swing_high_50": swing_high,
            "swing_low_50": swing_low,
            "prev_close": fib_level - 0.5,
            "close": fib_level + 0.2,
            "trend": 3.0,
            "atr": 1.5,
        }
    )
    features = Features(symbol="AAPL", computed_at=datetime.now(timezone.utc), values=values)
    signal = FibonacciPullbackStrategy().generate(features)
    assert signal is not None
    assert signal.confidence > 0.6
    assert "Fib pullback" in " ".join(signal.reasons)


def test_fibonacci_pullback_requires_proximity():
    values = _base_values()
    values.update(
        {
            "swing_high_50": 120.0,
            "swing_low_50": 100.0,
            "prev_close": 118.0,
            "close": 117.5,
            "trend": 3.0,
            "atr": 1.0,
        }
    )
    features = Features(symbol="AAPL", computed_at=datetime.now(timezone.utc), values=values)
    signal = FibonacciPullbackStrategy().generate(features)
    assert signal is None
