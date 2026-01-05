import pytest

from src.core.contracts import OrderRequest
from src.core.data.alpaca_client import MockAlpacaClient
from src.core.execution.execution_service import ExecutionService
from src.core.settings import LiveLockError, Settings


def test_live_lock_blocks_entry_without_unlock(monkeypatch):
    monkeypatch.delenv("TRADEBOT_LIVE_UNLOCK", raising=False)
    monkeypatch.delenv("TRADEBOT_LIVE_PIN", raising=False)
    settings = Settings(app={"mode": "live"}, live_unlock_pin="1234")
    service = ExecutionService(settings=settings, client=MockAlpacaClient())
    request = OrderRequest(symbol="AAPL", side="buy", quantity=1)
    with pytest.raises(LiveLockError):
        service.submit_order(request)


def test_live_lock_allows_exit_without_unlock():
    settings = Settings(app={"mode": "live"}, live_unlock_pin="1234")
    service = ExecutionService(settings=settings, client=MockAlpacaClient())
    request = OrderRequest(symbol="AAPL", side="sell", quantity=1)
    result = service.submit_order(request, allow_exit_without_unlock=True)
    assert result.status == "blocked"
