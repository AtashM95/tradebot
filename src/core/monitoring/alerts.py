from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests


class Notifier:
    def send(self, title: str, message: str) -> None:
        raise NotImplementedError


class ConsoleNotifier(Notifier):
    def send(self, title: str, message: str) -> None:
        logging.getLogger(__name__).warning("%s: %s", title, message)


@dataclass
class TelegramNotifier(Notifier):
    token: str
    chat_id: str

    def send(self, title: str, message: str) -> None:
        payload = {"chat_id": self.chat_id, "text": f"{title}\n{message}"}
        response = requests.post(f"https://api.telegram.org/bot{self.token}/sendMessage", json=payload, timeout=10)
        response.raise_for_status()


@dataclass
class AlertManager:
    cooldown_seconds: int
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    _last_sent: dict[str, datetime] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.console = ConsoleNotifier()
        self.telegram = None
        if self.telegram_token and self.telegram_chat_id:
            self.telegram = TelegramNotifier(self.telegram_token, self.telegram_chat_id)

    def send_alert(self, key: str, title: str, message: str) -> None:
        now = datetime.now(timezone.utc)
        last = self._last_sent.get(key)
        if last and now - last < timedelta(seconds=self.cooldown_seconds):
            return
        self._last_sent[key] = now
        self.console.send(title, message)
        if self.telegram:
            try:
                self.telegram.send(title, message)
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).warning("Telegram alert failed: %s", exc)
