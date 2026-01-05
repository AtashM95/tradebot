from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class HealthMonitor:
    started_at: datetime
    last_cycle_at: datetime | None = None

    def status(self) -> dict:
        uptime = datetime.now(timezone.utc) - self.started_at
        return {
            "status": "ok",
            "uptime_seconds": int(uptime.total_seconds()),
            "last_cycle_at": self.last_cycle_at.isoformat() if self.last_cycle_at else None,
        }

    def tick(self) -> None:
        self.last_cycle_at = datetime.now(timezone.utc)
