from __future__ import annotations

from dataclasses import dataclass

from src.core.contracts import Features, SignalIntent
from src.core.strategies.base import Strategy


def _build_intent(features: Features, confidence: float, reasons: list[str], strategy: str) -> SignalIntent:
    close = features.values["close"]
    atr = max(features.values.get("atr", 0.1), 0.1)
    stop = close - 2 * atr
    take_profit = close + 4 * atr
    return SignalIntent(
        symbol=features.symbol,
        confidence=confidence,
        entry=close,
        stop=stop,
        take_profit=take_profit,
        reasons=reasons,
        strategy=strategy,
        strength="strong" if confidence > 0.75 else "medium",
    )


@dataclass(frozen=True)
class TrendFollowingStrategy(Strategy):
    name: str = "trend_following"
    required_features: list[str] = None

    def __post_init__(self):
        object.__setattr__(self, "required_features", ["trend", "ema_fast", "ema_slow"])

    def generate(self, features: Features) -> SignalIntent | None:
        if features.values["trend"] > 0:
            return _build_intent(features, 0.72, ["EMA trend up"], self.name)
        return None


@dataclass(frozen=True)
class BreakoutStrategy(Strategy):
    name: str = "breakout"
    required_features: list[str] = None

    def __post_init__(self):
        object.__setattr__(self, "required_features", ["close", "vol_avg"])

    def generate(self, features: Features) -> SignalIntent | None:
        if features.values["close"] > 100 and features.values["vol_avg"] > 0:
            return _build_intent(features, 0.7, ["Price breakout above base"], self.name)
        return None


@dataclass(frozen=True)
class PullbackRetestStrategy(Strategy):
    name: str = "pullback_retest"
    required_features: list[str] = None

    def __post_init__(self):
        object.__setattr__(self, "required_features", ["ema_fast", "ema_slow"])

    def generate(self, features: Features) -> SignalIntent | None:
        if 0 < features.values["ema_fast"] - features.values["ema_slow"] < 1.0:
            return _build_intent(features, 0.68, ["Pullback near trend support"], self.name)
        return None


@dataclass(frozen=True)
class RSIMomentumStrategy(Strategy):
    name: str = "rsi_momentum"
    required_features: list[str] = None

    def __post_init__(self):
        object.__setattr__(self, "required_features", ["rsi"])

    def generate(self, features: Features) -> SignalIntent | None:
        if 55 <= features.values["rsi"] <= 70:
            return _build_intent(features, 0.66, ["RSI momentum in swing zone"], self.name)
        return None


@dataclass(frozen=True)
class CandlePatternStrategy(Strategy):
    name: str = "candle_patterns"
    required_features: list[str] = None

    def __post_init__(self):
        object.__setattr__(self, "required_features", ["close", "atr"])

    def generate(self, features: Features) -> SignalIntent | None:
        if features.values["atr"] > 0 and features.values["close"] > 0:
            return _build_intent(features, 0.64, ["Bullish candle cluster"], self.name)
        return None


@dataclass(frozen=True)
class FibonacciPullbackStrategy(Strategy):
    name: str = "fib_pullback"
    required_features: list[str] = None

    def __post_init__(self):
        object.__setattr__(self, "required_features", ["trend"])

    def generate(self, features: Features) -> SignalIntent | None:
        if features.values["trend"] > 0:
            return _build_intent(features, 0.69, ["Fib 38.2% pullback"], self.name)
        return None


@dataclass(frozen=True)
class VolumeConfirmationStrategy(Strategy):
    name: str = "volume_confirm"
    required_features: list[str] = None

    def __post_init__(self):
        object.__setattr__(self, "required_features", ["vol_avg"])

    def generate(self, features: Features) -> SignalIntent | None:
        if features.values["vol_avg"] > 0:
            return _build_intent(features, 0.63, ["Volume confirmation"], self.name)
        return None


def build_strategies() -> list[Strategy]:
    return [
        TrendFollowingStrategy(),
        BreakoutStrategy(),
        PullbackRetestStrategy(),
        RSIMomentumStrategy(),
        CandlePatternStrategy(),
        FibonacciPullbackStrategy(),
        VolumeConfirmationStrategy(),
    ]
