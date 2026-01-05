from src.core.contracts import FinalSignal
from src.core.portfolio.snapshot import PortfolioSnapshot
from src.core.risk.manager import RiskManager


def test_risk_manager_funding_alert():
    risk_manager = RiskManager(risk_per_trade=0.01, max_position_weight=0.1, cash_buffer=0.1)
    signal = FinalSignal(
        symbol="MSFT",
        score=0.8,
        entry=20.0,
        stop=19.0,
        take_profit=24.0,
        reasons=["test"],
        intents=[],
    )
    portfolio = PortfolioSnapshot(cash=50.0, equity=1000.0, open_positions=0)
    decision, funding = risk_manager.evaluate(signal, portfolio)
    assert not decision.approved
    assert funding is not None
    assert funding.missing_cash > 0
