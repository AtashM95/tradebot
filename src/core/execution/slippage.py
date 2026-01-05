from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SlippageModel:
    spread_bps: float
    fee_bps: float

    def estimate_cost(self, price: float, shares: int) -> float:
        notional = price * shares
        spread_cost = notional * (self.spread_bps / 10_000)
        fee_cost = notional * (self.fee_bps / 10_000)
        return spread_cost + fee_cost
