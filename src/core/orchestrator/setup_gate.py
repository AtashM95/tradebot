from __future__ import annotations

from dataclasses import dataclass

from src.core.contracts import Features


@dataclass
class SetupGate:
    min_trend: float = 0.0
    min_rsi: float = 45.0

    def allow(self, features: Features) -> tuple[bool, str]:
        trend = features.values.get("trend", 0.0)
        rsi = features.values.get("rsi", 0.0)
        close = features.values.get("close", 0.0)
        ema_slow = features.values.get("ema_slow", close)
        if trend <= self.min_trend:
            return False, "Trend pozitif değil"
        if rsi < self.min_rsi:
            return False, "RSI momentum eşiğinin altında"
        if close < ema_slow:
            return False, "Fiyat yavaş EMA altında"
        return True, "Fiyat aksiyonu kapısı geçti"
