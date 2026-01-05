from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.core.contracts import ExecutionReport, OrderRequest, OrderResult
from src.core.data.alpaca_client import AlpacaClient
from src.core.execution.order_manager import OrderManager
from src.core.settings import LiveLockError, Settings, enforce_live_lock


@dataclass
class ExecutionService:
    settings: Settings
    client: AlpacaClient
    order_manager: OrderManager | None = None
    live_session_until: Optional[datetime] = None

    def _session_active(self) -> bool:
        return self.live_session_until is not None and datetime.now(timezone.utc) < self.live_session_until

    def unlock_live_session(
        self,
        live_checkbox: bool,
        provided_pin: Optional[str],
        provided_phrase: Optional[str],
    ) -> datetime:
        enforce_live_lock(self.settings, live_checkbox, provided_pin, provided_phrase)
        duration = timedelta(minutes=self.settings.live_safety.session_minutes)
        self.live_session_until = datetime.now(timezone.utc) + duration
        return self.live_session_until

    def submit_order(
        self,
        request: OrderRequest,
        live_checkbox: bool = False,
        provided_pin: Optional[str] = None,
        provided_phrase: Optional[str] = None,
        allow_exit_without_unlock: bool = False,
    ) -> ExecutionReport:
        if self.settings.app.mode == "live":
            if not self._session_active() and not allow_exit_without_unlock:
                enforce_live_lock(self.settings, live_checkbox, provided_pin, provided_phrase)
        if request.side != "buy" and request.side != "sell":
            raise ValueError("Order side must be buy or sell.")
        if request.side == "sell" and request.quantity <= 0:
            raise ValueError("Sell orders must have positive quantity.")
        if request.side == "buy" and request.quantity <= 0:
            raise ValueError("Buy orders must have positive quantity.")
        if request.order_type == "limit" and request.limit_price is None:
            raise ValueError("Limit orders require limit_price.")
        if getattr(self.client, "is_mock", False):
            if self.settings.app.mode == "live":
                return ExecutionReport(
                    order_id="blocked-mock",
                    symbol=request.symbol,
                    status="blocked",
                    filled_qty=0,
                    average_fill_price=None,
                    raw={"mock": "true"},
                )
            result = self.client.submit_order(request)
            return ExecutionReport(
                order_id=result.order_id,
                symbol=result.symbol,
                status=result.status,
                filled_qty=result.filled_qty,
                average_fill_price=result.average_fill_price,
                raw=result.raw,
            )
        if self.order_manager:
            return self.order_manager.submit(request)
        result = self.client.submit_order(request)
        return ExecutionReport(
            order_id=result.order_id,
            symbol=result.symbol,
            status=result.status,
            filled_qty=result.filled_qty,
            average_fill_price=result.average_fill_price,
            raw=result.raw,
        )
