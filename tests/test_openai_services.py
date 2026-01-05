from src.core.settings import Settings
from src.integrations.openai_services import NewsRiskGateService, TradeExplainerService


def test_openai_disabled_news_gate_no_call(monkeypatch):
    called = {"value": False}

    def fake_call(*args, **kwargs):
        called["value"] = True
        return {}

    monkeypatch.setattr("src.integrations.openai_services.call_structured", fake_call)
    settings = Settings(openai_enabled=False)
    service = NewsRiskGateService(settings=settings)
    result = service.evaluate("AAPL", ["headline"], None, 100.0, 0.2)
    assert called["value"] is False
    assert result.trade_allowed is True
    assert result.risk_flag == "LOW"


def test_trade_explainer_schema_valid(monkeypatch):
    payload = {
        "decision": "ALLOW",
        "bullets": ["Trend aligned"],
        "key_factors": ["Setup gate passed"],
    }

    def fake_call(*args, **kwargs):
        return payload

    monkeypatch.setattr("src.integrations.openai_services.call_structured", fake_call)
    settings = Settings(openai_enabled=True)
    service = TradeExplainerService(settings=settings)
    result = service.explain(
        signal_intent={"symbol": "AAPL"},
        setup_gate={"allowed": True},
        indicators_snapshot={"rsi": 55},
        risk_decision={"approved": True},
    )
    assert result.decision == "ALLOW"
    assert result.bullets == ["Trend aligned"]
