from __future__ import annotations

from dataclasses import dataclass

from src.core.contracts import Features, SignalIntent
from src.core.settings import StrategyToggles
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
        object.__setattr__(
            self,
            "required_features",
            [
                "open",
                "high",
                "low",
                "close",
                "prev_open",
                "prev_high",
                "prev_low",
                "prev_close",
                "prev2_open",
                "prev2_high",
                "prev2_low",
                "prev2_close",
                "volume",
                "vol_avg",
                "trend",
                "atr",
            ],
        )

    def generate(self, features: Features) -> SignalIntent | None:
        values = features.values
        required = self.required_features or []
        if any(key not in values for key in required):
            return None
        open_ = values["open"]
        high = values["high"]
        low = values["low"]
        close = values["close"]
        prev_open = values["prev_open"]
        prev_close = values["prev_close"]
        prev_high = values["prev_high"]
        prev_low = values["prev_low"]
        prev2_open = values["prev2_open"]
        prev2_close = values["prev2_close"]
        prev2_high = values["prev2_high"]
        prev2_low = values["prev2_low"]
        volume = values["volume"]
        vol_avg = values["vol_avg"]
        trend = values["trend"]
        atr = max(values["atr"], 0.01)

        reasons: list[str] = []
        confidence = 0.0
        volume_bonus = 0.05 if volume >= vol_avg and vol_avg > 0 else 0.0

        # Bullish engulfing
        prev_bearish = prev_close < prev_open
        curr_bullish = close > open_
        body_engulfs = close >= prev_open and open_ <= prev_close
        if prev_bearish and curr_bullish and body_engulfs:
            confidence = 0.7 + volume_bonus
            reasons.append("Bullish engulfing pattern")

        # Hammer
        if confidence == 0.0:
            candle_range = max(high - low, 0.01)
            body = abs(close - open_)
            lower_shadow = min(open_, close) - low
            upper_shadow = high - max(open_, close)
            if (
                body / candle_range <= 0.3
                and lower_shadow >= 2 * body
                and upper_shadow <= body
                and trend <= 0
            ):
                confidence = 0.66 + volume_bonus
                reasons.append("Hammer reversal candle")

        # Morning star (3-candle reversal)
        if confidence == 0.0:
            first_bearish = prev2_close < prev2_open
            first_range = max(prev2_high - prev2_low, 0.01)
            second_range = max(prev_high - prev_low, 0.01)
            second_small = abs(prev_close - prev_open) / second_range <= 0.3
            third_bullish = close > open_
            close_above_mid = close >= (prev2_open + prev2_close) / 2
            if first_bearish and second_small and third_bullish and close_above_mid and trend <= 0:
                confidence = 0.72 + volume_bonus
                reasons.append("Morning star reversal")

        if confidence > 0.0:
            confidence = min(confidence + (0.02 if atr > 0 else 0.0), 0.9)
            return _build_intent(features, confidence, reasons, self.name)
        return None


@dataclass(frozen=True)
class FibonacciPullbackStrategy(Strategy):
    name: str = "fib_pullback"
    required_features: list[str] = None

    def __post_init__(self):
        object.__setattr__(
            self,
            "required_features",
            ["trend", "close", "prev_close", "swing_high_50", "swing_low_50", "atr", "volume", "vol_avg"],
        )

    def generate(self, features: Features) -> SignalIntent | None:
        values = features.values
        required = self.required_features or []
        if any(key not in values for key in required):
            return None
        trend = values["trend"]
        close = values["close"]
        prev_close = values["prev_close"]
        swing_high = values["swing_high_50"]
        swing_low = values["swing_low_50"]
        atr = max(values["atr"], 0.01)
        volume = values["volume"]
        vol_avg = values["vol_avg"]
        if trend <= 0 or swing_high <= swing_low:
            return None
        fib_range = swing_high - swing_low
        levels = {
            "38.2%": swing_high - fib_range * 0.382,
            "50%": swing_high - fib_range * 0.5,
            "61.8%": swing_high - fib_range * 0.618,
        }
        tolerance = max(atr * 0.35, 0.05)
        closest_name = None
        closest_level = None
        closest_distance = None
        for name, level in levels.items():
            distance = abs(close - level)
            if closest_distance is None or distance < closest_distance:
                closest_name = name
                closest_level = level
                closest_distance = distance
        if closest_distance is None or closest_level is None:
            return None
        if closest_distance > tolerance:
            return None
        bounced = prev_close < closest_level <= close
        if not bounced:
            return None
        proximity_score = max(0.0, 1 - closest_distance / tolerance)
        trend_score = min(abs(trend) / atr, 1.0) * 0.15
        volume_bonus = 0.05 if volume >= vol_avg and vol_avg > 0 else 0.0
        confidence = min(0.6 + proximity_score * 0.25 + trend_score + volume_bonus, 0.9)
        reasons = [f"Fib pullback to {closest_name} level", "Trend aligned"]
        return _build_intent(features, confidence, reasons, self.name)
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


def build_strategies(toggles: StrategyToggles | None = None) -> list[Strategy]:
    toggles = toggles or StrategyToggles()
    strategies: list[Strategy] = []
    if toggles.enable_trend_following:
        strategies.append(TrendFollowingStrategy())
    if toggles.enable_breakout:
        strategies.append(BreakoutStrategy())
    if toggles.enable_pullback_retest:
        strategies.append(PullbackRetestStrategy())
    if toggles.enable_rsi_momentum:
        strategies.append(RSIMomentumStrategy())
    if toggles.enable_candle_patterns:
        strategies.append(CandlePatternStrategy())
    if toggles.enable_fib_pullback:
        strategies.append(FibonacciPullbackStrategy())
    if toggles.enable_volume_confirm:
        strategies.append(VolumeConfirmationStrategy())
    return strategies
