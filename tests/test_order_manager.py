from dataclasses import dataclass

from src.core.contracts import OrderRequest, OrderResult
from src.core.execution.order_manager import OrderManager


@dataclass
class DummyClient:
    submit_calls: int = 0
    cancel_calls: int = 0

    def submit_order(self, request: OrderRequest) -> OrderResult:
        self.submit_calls += 1
        return OrderResult(
            order_id=f"order-{self.submit_calls}",
            symbol=request.symbol,
            status="accepted",
            filled_qty=0,
            average_fill_price=None,
            raw={},
        )

    def cancel_order(self, order_id: str) -> None:
        self.cancel_calls += 1


def test_order_manager_idempotency():
    client = DummyClient()
    manager = OrderManager(client=client, ttl_minutes=10)
    request = OrderRequest(symbol="AAPL", side="buy", quantity=10, idempotency_key="key-1")
    first = manager.submit(request)
    second = manager.submit(request)
    assert first.order_id == second.order_id
    assert client.submit_calls == 1


def test_order_manager_partial_fill_update():
    client = DummyClient()
    manager = OrderManager(client=client, ttl_minutes=10)
    request = OrderRequest(symbol="AAPL", side="buy", quantity=10, idempotency_key="key-2")
    report = manager.submit(request)
    manager.record_fill("key-2", filled_qty=4, avg_price=100.0)
    assert report.status == "partially_filled"
    assert report.filled_qty == 4


def test_order_manager_purges_stale_orders():
    client = DummyClient()
    manager = OrderManager(client=client, ttl_minutes=0)
    request = OrderRequest(symbol="AAPL", side="buy", quantity=10, idempotency_key="key-3")
    report = manager.submit(request)
    report.status = "accepted"
    expired = manager.purge_stale_orders()
    assert "key-3" in expired
    assert client.cancel_calls == 1
