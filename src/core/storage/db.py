from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


@dataclass
class SQLiteStore:
    database_url: str

    def __post_init__(self) -> None:
        self._path = self._resolve_path(self.database_url)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @staticmethod
    def _resolve_path(database_url: str) -> Path:
        if database_url.startswith("sqlite:///"):
            return Path(database_url.replace("sqlite:///", "", 1))
        if database_url.startswith("sqlite://"):
            return Path(database_url.replace("sqlite://", "", 1))
        return Path(database_url)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                score REAL NOT NULL,
                entry REAL NOT NULL,
                stop REAL NOT NULL,
                take_profit REAL NOT NULL,
                reasons TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry REAL NOT NULL,
                stop REAL NOT NULL,
                take_profit REAL NOT NULL,
                status TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                closed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS fills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                filled_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS funding_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                missing_cash REAL NOT NULL,
                proposed_actions TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trade_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                payload TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
            )

    def seed_watchlist(self, symbols: Iterable[str]) -> None:
        if self.get_watchlist():
            return
        self.set_watchlist(list(symbols))

    def get_watchlist(self) -> list[str]:
        with self._connect() as conn:
            cursor = conn.execute("SELECT symbol FROM watchlist ORDER BY symbol")
            return [row["symbol"] for row in cursor.fetchall()]

    def set_watchlist(self, symbols: list[str]) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watchlist")
            now = datetime.now(timezone.utc).isoformat()
            cursor.executemany(
                "INSERT INTO watchlist (symbol, created_at) VALUES (?, ?)",
                [(symbol, now) for symbol in symbols],
            )

    def add_signal(self, symbol: str, score: float, entry: float, stop: float, take_profit: float, reasons: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO signals (symbol, score, entry, stop, take_profit, reasons, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (symbol, score, entry, stop, take_profit, reasons, datetime.now(timezone.utc).isoformat()),
            )

    def add_trade(self, symbol: str, side: str, quantity: int, entry: float, stop: float, take_profit: float) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO trades (symbol, side, quantity, entry, stop, take_profit, status, opened_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (symbol, side, quantity, entry, stop, take_profit, "open", datetime.now(timezone.utc).isoformat()),
            )
            return int(cursor.lastrowid)

    def close_trade(self, trade_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE trades SET status = ?, closed_at = ? WHERE id = ?",
                ("closed", datetime.now(timezone.utc).isoformat(), trade_id),
            )

    def update_trade_stop(self, trade_id: int, new_stop: float) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE trades SET stop = ? WHERE id = ?", (new_stop, trade_id))

    def list_open_trades(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute("SELECT * FROM trades WHERE status = 'open' ORDER BY opened_at")
            return cursor.fetchall()

    def add_fill(self, trade_id: int | None, symbol: str, quantity: int, price: float) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO fills (trade_id, symbol, quantity, price, filled_at) VALUES (?, ?, ?, ?, ?)",
                (trade_id, symbol, quantity, price, datetime.now(timezone.utc).isoformat()),
            )

    def add_funding_alert(self, symbol: str, missing_cash: float, proposed_actions: str, details: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO funding_alerts (symbol, missing_cash, proposed_actions, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (symbol, missing_cash, proposed_actions, details, datetime.now(timezone.utc).isoformat()),
            )

    def list_funding_alerts(self, limit: int = 50) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM funding_alerts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            return cursor.fetchall()

    def enqueue_trade(self, symbol: str, payload: str, ttl_hours: int) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO trade_queue (symbol, payload, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (symbol, payload, expires_at.isoformat(), datetime.now(timezone.utc).isoformat()),
            )

    def list_trade_queue(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM trade_queue ORDER BY created_at DESC",
            )
            return cursor.fetchall()

    def purge_expired_queue(self) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM trade_queue WHERE expires_at < ?", (now,))
            return cursor.rowcount

    def add_log(self, level: str, message: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO logs (level, message, created_at) VALUES (?, ?, ?)",
                (level, message, datetime.now(timezone.utc).isoformat()),
            )

    def list_logs(self, limit: int = 100) -> list[sqlite3.Row]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM logs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            return cursor.fetchall()
