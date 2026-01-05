import types

from src.core.monitoring import notifications


def test_notifications_delivered_with_plyer(monkeypatch):
    fake_plyer = types.ModuleType("plyer")
    fake_plyer.notification = types.SimpleNamespace(notify=lambda **_kwargs: None)
    monkeypatch.setitem(  # type: ignore[arg-type]
        notifications.sys.modules,
        "plyer",
        fake_plyer,
    )
    result = notifications.send_desktop_notification("Test", "Message")
    assert result.delivered is True


def test_notifications_fallback(monkeypatch):
    monkeypatch.delitem(notifications.sys.modules, "plyer", raising=False)
    result = notifications.send_desktop_notification("Test", "Message")
    assert result.delivered is False
