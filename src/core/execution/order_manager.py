from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from src.core.contracts import ExecutionReport, OrderRequest
from src.core.data.alpaca_client import AlpacaClient


@dataclass
class ManagedOrder:
    request: OrderRequest
    report: ExecutionReport
    created_at: datetime


@dataclass
class OrderManager:
    client: AlpacaClient
    ttl_minutes: int
    _orders: dict[str, ManagedOrder] = field(default_factory=dict)

    def submit(self, request: OrderRequest) -> ExecutionReport:
        if request.idempotency_key:
            existing = self._orders.get(request.idempotency_key)
            if existing:
                return existing.report
        result = self.client.submit_order(request)
        report = ExecutionReport(
            order_id=result.order_id,
            symbol=result.symbol,
            status=result.status,
            filled_qty=result.filled_qty,
            average_fill_price=result.average_fill_price,
            idempotency_key=request.idempotency_key,
            raw=result.raw,
        )
        if request.idempotency_key:
            self._orders[request.idempotency_key] = ManagedOrder(
                request=request,
                report=report,
                created_at=datetime.now(timezone.utc),
            )
        return report

    def cancel(self, order_id: str) -> None:
        self.client.cancel_order(order_id)

    def replace(self, request: OrderRequest) -> ExecutionReport:
        return self.submit(request)

    def record_fill(self, idempotency_key: str, filled_qty: int, avg_price: float | None) -> None:
        managed = self._orders.get(idempotency_key)
        if not managed:
            return
        status = "filled" if filled_qty >= managed.request.quantity else "partially_filled"
        managed.report.status = status
        managed.report.filled_qty = filled_qty
        managed.report.average_fill_price = avg_price

    def purge_stale_orders(self) -> list[str]:
        now = datetime.now(timezone.utc)
        expired: list[str] = []
        ttl = timedelta(minutes=self.ttl_minutes)
        for key, managed in list(self._orders.items()):
            if now - managed.created_at > ttl and managed.report.status in {"accepted", "pending", "new"}:
                self.cancel(managed.report.order_id)
                managed.report.status = "canceled"
                expired.append(key)
        return expired
