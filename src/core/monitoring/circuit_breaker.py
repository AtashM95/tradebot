from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class CircuitBreaker:
    max_failures: int
    drawdown_limit: float
    cooldown_minutes: int
    manual_override_until: Optional[datetime] = None
    consecutive_failures: int = 0
    halted_until: Optional[datetime] = None
    last_reason: str = ""
    last_triggered_at: Optional[datetime] = None

    def can_trade(self, drawdown: float, connectivity_ok: bool) -> tuple[bool, str]:
        now = datetime.now(timezone.utc)
        if self.manual_override_until and now < self.manual_override_until:
            return True, "manual_override"
        if self.halted_until and now < self.halted_until:
            return False, self.last_reason or "cooldown"
        if drawdown >= self.drawdown_limit:
            self._trigger("drawdown_limit")
            return False, "drawdown_limit"
        if not connectivity_ok and self.consecutive_failures >= self.max_failures:
            self._trigger("connectivity_failures")
            return False, "connectivity_failures"
        return True, "ok"

    def record_failure(self, reason: str) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.max_failures:
            self._trigger(reason)

    def record_success(self) -> None:
        self.consecutive_failures = 0

    def manual_override(self, minutes: int) -> None:
        self.manual_override_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    def _trigger(self, reason: str) -> None:
        self.last_reason = reason
        self.last_triggered_at = datetime.now(timezone.utc)
        self.halted_until = self.last_triggered_at + timedelta(minutes=self.cooldown_minutes)
