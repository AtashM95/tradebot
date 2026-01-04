from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PortfolioSnapshot:
    cash: float
    equity: float
    open_positions: int

    @classmethod
    def from_account(cls, account: dict) -> "PortfolioSnapshot":
        cash = float(account.get("cash", 0.0))
        equity = float(account.get("portfolio_value", cash))
        return cls(cash=cash, equity=equity, open_positions=int(account.get("positions", 0)))
