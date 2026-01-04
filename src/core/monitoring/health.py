from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class HealthMonitor:
    started_at: datetime

    def status(self) -> dict:
        uptime = datetime.utcnow() - self.started_at
        return {
            "status": "ok",
            "uptime_seconds": int(uptime.total_seconds()),
        }
