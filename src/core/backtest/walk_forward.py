from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from src.core.ensemble.aggregator import EnsembleAggregator
from src.core.features.feature_engine import FeatureEngine
from src.core.portfolio.snapshot import PortfolioSnapshot
from src.core.risk.manager import RiskManager
from src.core.strategies.strategies import build_strategies
from src.core.data.market_data import MarketDataProvider


@dataclass
class WalkForwardBacktester:
    data_provider: Optional[MarketDataProvider] = None
    feature_engine: Optional[FeatureEngine] = None
    ensemble: Optional[EnsembleAggregator] = None
    risk_manager: Optional[RiskManager] = None
    initial_cash: float = 100000.0
    train_days: int = 504
    test_days: int = 126
    step_days: int = 63

    def run(self, symbols: list[str], years: int = 5) -> dict:
        if not symbols:
            raise ValueError("Geri test için en az bir sembol gereklidir.")
        if self.data_provider is None:
            raise ValueError("Walk-forward için MarketDataProvider gereklidir.")
        feature_engine = self.feature_engine or FeatureEngine()
        ensemble = self.ensemble or EnsembleAggregator()
        risk_manager = self.risk_manager or RiskManager(risk_per_trade=0.005, max_position_weight=0.12, cash_buffer=0.08)
        max_bars = int(years * 252)
        folds: list[dict] = []
        equity_curves: list[float] = []
        for symbol in symbols:
            bars = self.data_provider.get_daily_bars(symbol, limit=max_bars)
            if len(bars) < self.train_days + self.test_days:
                continue
            fold_start = 0
            while fold_start + self.train_days + self.test_days <= len(bars):
                train_slice = bars.iloc[fold_start : fold_start + self.train_days]
                test_slice = bars.iloc[fold_start + self.train_days : fold_start + self.train_days + self.test_days]
                fold_result = self._run_fold(
                    symbol=symbol,
                    train_slice=train_slice,
                    test_slice=test_slice,
                    feature_engine=feature_engine,
                    ensemble=ensemble,
                    risk_manager=risk_manager,
                )
                folds.append(fold_result)
                equity_curves.extend(fold_result["equity_curve"])
                fold_start += self.step_days

        aggregate = self._aggregate_metrics(folds, equity_curves)
        summary = f"{len(folds)} folds, avg return {aggregate.get('total_return', 0.0):.2%}"
        return {
            "symbols": symbols,
            "folds": folds,
            "aggregate": aggregate,
            "config": {
                "years": years,
                "train_days": self.train_days,
                "test_days": self.test_days,
                "step_days": self.step_days,
            },
            "summary": summary,
        }

    def _run_fold(
        self,
        symbol: str,
        train_slice: pd.DataFrame,
        test_slice: pd.DataFrame,
        feature_engine: FeatureEngine,
        ensemble: EnsembleAggregator,
        risk_manager: RiskManager,
    ) -> dict:
        cash = self.initial_cash
        shares = 0
        entry_price = 0.0
        stop = 0.0
        take_profit = 0.0
        equity_curve: list[float] = []
        trades: list[float] = []
        for idx in range(len(test_slice)):
            history = pd.concat([train_slice, test_slice.iloc[: idx + 1]])
            features = feature_engine.compute(symbol, history)
            intents = [signal for strategy in build_strategies() if (signal := strategy.generate(features))]
            final = ensemble.aggregate(intents)
            bar = test_slice.iloc[idx]
            if shares > 0:
                exit_price = None
                if bar["low"] <= stop:
                    exit_price = stop
                elif bar["high"] >= take_profit:
                    exit_price = take_profit
                if exit_price is not None:
                    cash += shares * exit_price
                    trades.append((exit_price - entry_price) * shares)
                    shares = 0
                    entry_price = 0.0
                    stop = 0.0
                    take_profit = 0.0
            if shares == 0 and final is not None:
                portfolio = PortfolioSnapshot(cash=cash, equity=cash, open_positions=0)
                decision, _ = risk_manager.evaluate(final, portfolio)
                if decision.approved:
                    shares = decision.shares
                    entry_price = final.entry
                    stop = final.stop
                    take_profit = final.take_profit
                    cash -= shares * entry_price
            position_value = shares * bar["close"]
            equity = cash + position_value
            equity_curve.append(equity)
        metrics = self._compute_metrics(equity_curve, trades)
        return {
            "symbol": symbol,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "equity_curve": equity_curve,
        }

    @staticmethod
    def _compute_metrics(equity_curve: list[float], trades: list[float]) -> dict:
        if not equity_curve:
            return {
                "total_return": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "sharpe": 0.0,
                "trades": 0,
            }
        returns = np.diff(equity_curve) / np.maximum(equity_curve[:-1], 1)
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
        peak = equity_curve[0]
        max_drawdown = 0.0
        for value in equity_curve:
            peak = max(peak, value)
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        wins = [trade for trade in trades if trade > 0]
        losses = [trade for trade in trades if trade < 0]
        win_rate = len(wins) / len(trades) if trades else 0.0
        profit_factor = (sum(wins) / abs(sum(losses))) if losses else float(len(wins) > 0)
        sharpe = 0.0
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        return {
            "total_return": float(total_return),
            "max_drawdown": float(max_drawdown),
            "win_rate": float(win_rate),
            "profit_factor": float(profit_factor),
            "sharpe": float(sharpe),
            "trades": len(trades),
        }

    @staticmethod
    def _aggregate_metrics(folds: list[dict], equity_curve: list[float]) -> dict:
        if not folds:
            return {
                "total_return": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "sharpe": 0.0,
                "trades": 0,
            }
        metrics_list = [fold["metrics"] for fold in folds]
        aggregate = {}
        for key in ["total_return", "max_drawdown", "win_rate", "profit_factor", "sharpe", "trades"]:
            aggregate[key] = float(np.mean([metric[key] for metric in metrics_list]))
        aggregate["equity_samples"] = len(equity_curve)
        return aggregate
