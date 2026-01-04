from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.core.contracts import OrderRequest, OrderResult
from src.core.data.alpaca_client import AlpacaClient
from src.core.settings import Settings, enforce_live_lock


@dataclass
class ExecutionService:
    settings: Settings
    client: AlpacaClient

    def submit_order(
        self,
        request: OrderRequest,
        live_checkbox: bool = False,
        provided_pin: Optional[str] = None,
        provided_phrase: Optional[str] = None,
    ) -> OrderResult:
        if self.settings.app.mode == "live":
            enforce_live_lock(self.settings, live_checkbox, provided_pin, provided_phrase)
        return self.client.submit_order(request)
