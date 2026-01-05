from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from src.core.contracts import OrderRequest, OrderResult
from src.core.data.alpaca_client import AlpacaClient
from src.core.settings import LiveLockError, Settings, enforce_live_lock


@dataclass
class ExecutionService:
    settings: Settings
    client: AlpacaClient
    live_session_until: Optional[datetime] = None

    def _session_active(self) -> bool:
        return self.live_session_until is not None and datetime.utcnow() < self.live_session_until

    def unlock_live_session(
        self,
        live_checkbox: bool,
        provided_pin: Optional[str],
        provided_phrase: Optional[str],
    ) -> datetime:
        enforce_live_lock(self.settings, live_checkbox, provided_pin, provided_phrase)
        duration = timedelta(minutes=self.settings.live_safety.session_minutes)
        self.live_session_until = datetime.utcnow() + duration
        return self.live_session_until

    def submit_order(
        self,
        request: OrderRequest,
        live_checkbox: bool = False,
        provided_pin: Optional[str] = None,
        provided_phrase: Optional[str] = None,
    ) -> OrderResult:
        if self.settings.app.mode == "live":
            if not self._session_active():
                if live_checkbox or provided_pin or provided_phrase:
                    self.unlock_live_session(live_checkbox, provided_pin, provided_phrase)
                if not self._session_active():
                    raise LiveLockError("LIVE kilidi: aktif oturum yok.")
        if request.side != "buy" and request.side != "sell":
            raise ValueError("Emir yönü buy veya sell olmalıdır.")
        if request.side == "sell" and request.quantity <= 0:
            raise ValueError("Sell emirlerinde adet pozitif olmalıdır.")
        if request.side == "buy" and request.quantity <= 0:
            raise ValueError("Buy emirlerinde adet pozitif olmalıdır.")
        if getattr(self.client, "is_mock", False):
            return OrderResult(
                order_id="blocked-mock",
                symbol=request.symbol,
                status="blocked",
                filled_qty=0,
                average_fill_price=None,
                raw={"mock": "true"},
            )
        return self.client.submit_order(request)
