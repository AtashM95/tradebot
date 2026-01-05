from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from src.core.storage.db import SQLiteStore


@dataclass
class TradeQueue:
    store: SQLiteStore
    ttl_hours: int

    def enqueue(self, symbol: str, payload: dict) -> None:
        self.store.enqueue_trade(symbol, json.dumps(payload), self.ttl_hours)

    def list_active(self) -> list[dict]:
        self.store.purge_expired_queue()
        rows = self.store.list_trade_queue()
        items = []
        for row in rows:
            items.append(
                {
                    "id": row["id"],
                    "symbol": row["symbol"],
                    "payload": json.loads(row["payload"]),
                    "expires_at": row["expires_at"],
                    "created_at": row["created_at"],
                    "expired": datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc),
                }
            )
        return items
