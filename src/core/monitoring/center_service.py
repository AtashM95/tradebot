from __future__ import annotations

from dataclasses import dataclass

from src.core.contracts import FinalSignal, OrderRequest, SignalIntent, TestCenterCheck
from src.core.data.market_data import MarketDataProvider
from src.core.ensemble.aggregator import EnsembleAggregator
from src.core.features.feature_engine import FeatureEngine
from src.core.portfolio.snapshot import PortfolioSnapshot
from src.core.risk.manager import RiskManager
from src.core.strategies.strategies import build_strategies
from src.core.backtest.walk_forward import WalkForwardBacktester
from src.core.execution.execution_service import ExecutionService
from src.core.settings import StrategyToggles


@dataclass
class TestCenterService:
    data_provider: MarketDataProvider
    feature_engine: FeatureEngine
    ensemble: EnsembleAggregator
    risk_manager: RiskManager
    execution: ExecutionService
    backtester: WalkForwardBacktester
    strategy_toggles: StrategyToggles | None = None

    def run_checks(self) -> list[TestCenterCheck]:
        checks: list[TestCenterCheck] = []
        checks.append(self._account_check())
        checks.append(self._data_check())
        checks.append(self._dry_run_check())
        checks.append(self._paper_order_check())
        checks.append(self._funding_alert_check())
        checks.append(self._backtest_check())
        return checks

    def _account_check(self) -> TestCenterCheck:
        try:
            account = self.execution.client.get_account()
            return TestCenterCheck(
                name="Hesap Kontrolü (deneme)",
                status="pass",
                message="Alpaca hesabı erişilebilir.",
                details={"cash": str(account.get("cash", ""))},
            )
        except Exception as exc:  # noqa: BLE001
            return TestCenterCheck(
                name="Hesap Kontrolü (deneme)",
                status="fail",
                message=str(exc),
                next_step="ALPACA_PAPER_API_KEY ve ALPACA_PAPER_SECRET_KEY değerlerini .env içinde ayarlayın.",
            )

    def _data_check(self) -> TestCenterCheck:
        try:
            bars = self.data_provider.get_daily_bars("AAPL", limit=120)
            features = self.feature_engine.compute("AAPL", bars)
            return TestCenterCheck(
                name="Veri Kontrolü",
                status="pass",
                message="AAPL barları ve özellikler hesaplandı.",
                details={"close": f"{features.values['close']:.2f}"},
            )
        except Exception as exc:  # noqa: BLE001
            return TestCenterCheck(
                name="Veri Kontrolü",
                status="fail",
                message=str(exc),
                next_step="Alpaca veri kimlik bilgilerini veya cache dizini izinlerini kontrol edin.",
            )

    def _dry_run_check(self) -> TestCenterCheck:
        try:
            bars = self.data_provider.get_daily_bars("MSFT", limit=120)
            features = self.feature_engine.compute("MSFT", bars)
            intents = [
                signal
                for strategy in build_strategies(self.strategy_toggles)
                if (signal := strategy.generate(features)) is not None
            ]
            final = self.ensemble.aggregate(intents)
            if final is None:
                raise ValueError("Nihai sinyal üretilemedi.")
            portfolio = PortfolioSnapshot(cash=500.0, equity=500.0, open_positions=0)
            decision, _ = self.risk_manager.evaluate(final, portfolio)
            if not decision.approved:
                raise ValueError("Risk yöneticisi dry-run işlemini veto etti.")
            return TestCenterCheck(
                name="Dry-Run Kontrolü",
                status="pass",
                message="SignalIntent ve RiskDecision üretildi.",
            )
        except Exception as exc:  # noqa: BLE001
            return TestCenterCheck(
                name="Dry-Run Kontrolü",
                status="fail",
                message=str(exc),
                next_step="Strateji anahtarlarını ve risk ayarlarını kontrol edin.",
            )

    def _paper_order_check(self) -> TestCenterCheck:
        try:
            request = OrderRequest(symbol="SPY", side="buy", quantity=1)
            result = self.execution.submit_order(request)
            return TestCenterCheck(
                name="Deneme Emir Kontrolü",
                status="pass",
                message="Paper emir gönderildi.",
                details={"order_id": result.order_id},
            )
        except Exception as exc:  # noqa: BLE001
            return TestCenterCheck(
                name="Deneme Emir Kontrolü",
                status="fail",
                message=str(exc),
                next_step="Alpaca paper anahtarlarını ve piyasa saatlerini doğrulayın.",
            )

    def _funding_alert_check(self) -> TestCenterCheck:
        try:
            signal = FinalSignal(
                symbol="NVDA",
                score=0.8,
                entry=500.0,
                stop=480.0,
                take_profit=560.0,
                reasons=["test"],
                intents=[
                    SignalIntent(
                        symbol="NVDA",
                        confidence=0.8,
                        entry=500.0,
                        stop=480.0,
                        take_profit=560.0,
                        reasons=["test"],
                        strategy="trend_following",
                    )
                ],
            )
            portfolio = PortfolioSnapshot(cash=50.0, equity=500.0, open_positions=5)
            decision, funding = self.risk_manager.evaluate(signal, portfolio)
            if funding is None or decision.approved:
                raise ValueError("Fonlama uyarısı tetiklenmedi.")
            return TestCenterCheck(
                name="Fonlama Uyarısı Kontrolü",
                status="pass",
                message="Fonlama uyarısı swap/partial/queue önerileriyle üretildi.",
            )
        except Exception as exc:  # noqa: BLE001
            return TestCenterCheck(
                name="Fonlama Uyarısı Kontrolü",
                status="fail",
                message=str(exc),
                next_step="Fonlama eşiği veya cash buffer ayarlarını kontrol edin.",
            )

    def _backtest_check(self) -> TestCenterCheck:
        try:
            report = self.backtester.run(["SPY", "AAPL"], years=5)
            return TestCenterCheck(
                name="Geri Test Kontrolü",
                status="pass",
                message="Walk-forward geri test tamamlandı.",
                details={"summary": report.get("summary", "")},
            )
        except NotImplementedError as exc:
            return TestCenterCheck(
                name="Geri Test Kontrolü",
                status="warn",
                message=str(exc),
                next_step="Backtest modülü tamamlanana kadar bu kontrol bilgilendirme amaçlıdır.",
            )
        except Exception as exc:  # noqa: BLE001
            return TestCenterCheck(
                name="Geri Test Kontrolü",
                status="fail",
                message=str(exc),
                next_step="Veri cache ve geri test ayarlarını doğrulayın.",
            )
