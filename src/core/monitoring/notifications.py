from __future__ import annotations

from dataclasses import dataclass
import logging
import sys


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
    logger = logging.getLogger(__name__)
    try:
        from plyer import notification as plyer_notification

        plyer_notification.notify(title=title, message=message, timeout=5)
        return NotificationResult(delivered=True, channel="plyer", detail="Notification delivered via plyer.")
    except Exception:  # noqa: BLE001
        pass

    if sys.platform.startswith("win"):
        try:
            from win10toast import ToastNotifier

            notifier = ToastNotifier()
            notifier.show_toast(title, message, duration=5, threaded=True)
            return NotificationResult(delivered=True, channel="win10toast", detail="Notification delivered via win10toast.")
        except Exception:  # noqa: BLE001
            pass

        try:
            from winotify import Notification

            toast = Notification(app_id="TradeBot", title=title, msg=message)
            toast.show()
            return NotificationResult(delivered=True, channel="winotify", detail="Notification delivered via winotify.")
        except Exception:  # noqa: BLE001
            pass

    hint = "Install plyer (pip install plyer) or win10toast/winotify on Windows to enable notifications."
    logger.warning("Desktop notification not delivered. %s", hint)
    return NotificationResult(delivered=False, channel="noop", detail=f"{title}: {message} ({hint})")
