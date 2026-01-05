from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.core.contracts import FinalSignal, OrderResult


@dataclass
class JournalEntry:
    ts: datetime
    event: str
    payload: dict


@dataclass
class Journal:
    entries: list[JournalEntry] = field(default_factory=list)

    def record_signal(self, signal: FinalSignal) -> None:
        self.entries.append(
            JournalEntry(ts=datetime.now(timezone.utc), event="signal", payload=signal.model_dump())
        )

    def record_order(self, result: OrderResult) -> None:
        self.entries.append(
            JournalEntry(ts=datetime.now(timezone.utc), event="order", payload=result.model_dump())
        )
