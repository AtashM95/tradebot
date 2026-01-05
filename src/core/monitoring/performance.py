from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PerformanceMonitor:
    equity_curve: list[float] = field(default_factory=list)
    peak_equity: float = 0.0
    max_drawdown: float = 0.0
    trade_pnls: list[float] = field(default_factory=list)
    consecutive_losses: int = 0
    exposure: float = 0.0

    def update_equity(self, equity: float, exposure: float) -> None:
        self.equity_curve.append(equity)
        if equity > self.peak_equity:
            self.peak_equity = equity
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - equity) / self.peak_equity
            self.max_drawdown = max(self.max_drawdown, drawdown)
        self.exposure = exposure

    def record_trade(self, pnl: float) -> None:
        self.trade_pnls.append(pnl)
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def win_rate(self) -> float:
        if not self.trade_pnls:
            return 0.0
        wins = len([pnl for pnl in self.trade_pnls if pnl > 0])
        return wins / len(self.trade_pnls)

    def drawdown(self) -> float:
        return self.max_drawdown
