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


def test_notifications_fallback(monkeypatch, caplog):
    monkeypatch.delitem(notifications.sys.modules, "plyer", raising=False)
    monkeypatch.delitem(notifications.sys.modules, "win10toast", raising=False)
    monkeypatch.delitem(notifications.sys.modules, "winotify", raising=False)
    caplog.set_level("WARNING")
    result = notifications.send_desktop_notification("Test", "Message")
    assert result.delivered is False
    assert any("Desktop notification not delivered" in record.message for record in caplog.records)
