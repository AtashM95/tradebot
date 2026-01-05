from __future__ import annotations

from dataclasses import dataclass

from src.core.contracts import FinalSignal, FundingAlert, RiskDecision
from src.core.portfolio.snapshot import PortfolioSnapshot


@dataclass
class RiskManager:
    risk_per_trade: float
    max_position_weight: float
    cash_buffer: float

    def evaluate(self, signal: FinalSignal, portfolio: PortfolioSnapshot) -> tuple[RiskDecision, FundingAlert | None]:
        reasons: list[str] = []
        if signal.entry <= 0 or signal.stop <= 0 or signal.entry <= signal.stop:
            return (
                RiskDecision(
                    symbol=signal.symbol,
                    outcome="veto",
                    approved=False,
                    shares=0,
                    cash_required=0.0,
                    reasons=["Invalid entry/stop configuration"],
                    constraints={},
                ),
                None,
            )
        risk_per_share = signal.entry - signal.stop
        if risk_per_share <= 0:
            return (
                RiskDecision(
                    symbol=signal.symbol,
                    outcome="veto",
                    approved=False,
                    shares=0,
                    cash_required=0.0,
                    reasons=["Invalid risk per share"],
                    constraints={},
                ),
                None,
            )
        equity = portfolio.equity
        max_cash = equity * self.max_position_weight
        target_risk_cash = equity * self.risk_per_trade
        shares = int(min(max_cash / signal.entry, target_risk_cash / risk_per_share))
        if shares <= 0:
            return (
                RiskDecision(
                    symbol=signal.symbol,
                    outcome="veto",
                    approved=False,
                    shares=0,
                    cash_required=0.0,
                    reasons=["Position size below minimum"],
                    constraints={},
                ),
                None,
            )
        cash_required = shares * signal.entry
        available_cash = portfolio.cash * (1 - self.cash_buffer)
        if cash_required > available_cash:
            missing = cash_required - available_cash
            funding = FundingAlert(
                missing_cash=missing,
                proposed_actions=["swap", "trim", "partial_entry", "trade_queue"],
                details={"cash_required": cash_required, "available_cash": available_cash},
            )
            reasons.append("Insufficient cash, funding alert created")
            decision = RiskDecision(
                symbol=signal.symbol,
                outcome="veto",
                approved=False,
                shares=0,
                cash_required=cash_required,
                reasons=reasons,
                constraints={"max_position_weight": self.max_position_weight, "risk_per_trade": self.risk_per_trade},
            )
            return decision, funding
        reasons.append("Risk checks passed")
        decision = RiskDecision(
            symbol=signal.symbol,
            outcome="approved",
            approved=True,
            shares=shares,
            cash_required=cash_required,
            reasons=reasons,
            constraints={"max_position_weight": self.max_position_weight, "risk_per_trade": self.risk_per_trade},
        )
        return decision, None
