from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NotificationResult:
    delivered: bool
    channel: str
    detail: str


def send_desktop_notification(title: str, message: str) -> NotificationResult:
    """
    Desktop notification hook.

    If a native notifier is not available, returns a not-delivered result
    while still providing a structured response for logging.
    """
    return NotificationResult(delivered=False, channel="noop", detail=f"{title}: {message}")
