from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional


class BotError(Exception):
    pass


class RecoverableError(BotError):
    pass


class FatalError(BotError):
    pass


class DataValidationError(RecoverableError):
    pass


class ConnectivityError(RecoverableError):
    pass


class OrderError(RecoverableError):
    pass


class ConfigError(FatalError):
    pass


@dataclass
class ErrorHandler:
    max_retries: int
    retry_delay_seconds: int
    alert_hook: Optional[callable] = None

    def handle(self, exc: Exception, context: str) -> str:
        logger = logging.getLogger(__name__)
        classification = self.classify(exc)
        logger.error("Error in %s: %s", context, exc, exc_info=True)
        if self.alert_hook:
            self.alert_hook(f"{classification}: {context} -> {exc}")
        return classification

    def classify(self, exc: Exception) -> str:
        if isinstance(exc, FatalError):
            return "fatal"
        if isinstance(exc, RecoverableError):
            return "recoverable"
        return "unknown"
