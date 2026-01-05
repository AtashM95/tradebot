from datetime import datetime, timezone

from src.core.contracts import Features
from src.core.orchestrator.setup_gate import SetupGate


def test_setup_gate_respects_thresholds():
    gate = SetupGate(min_trend=1.0, min_rsi=60.0)
    features = Features(
        symbol="AAPL",
        computed_at=datetime.now(timezone.utc),
        values={"trend": 0.5, "rsi": 55.0, "close": 100.0, "ema_slow": 99.0},
    )
    allowed, reason = gate.allow(features)
    assert allowed is False
    assert "Trend" in reason or "RSI" in reason
