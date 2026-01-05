from datetime import datetime, timedelta, timezone

from src.core.monitoring.circuit_breaker import CircuitBreaker


def test_circuit_breaker_triggers_on_failures():
    breaker = CircuitBreaker(max_failures=2, drawdown_limit=0.2, cooldown_minutes=10)
    breaker.record_failure("connectivity")
    assert breaker.can_trade(drawdown=0.0, connectivity_ok=False)[0] is True
    breaker.record_failure("connectivity")
    allowed, reason = breaker.can_trade(drawdown=0.0, connectivity_ok=False)
    assert allowed is False
    assert reason == "connectivity_failures" or reason == "connectivity"


def test_circuit_breaker_manual_override():
    breaker = CircuitBreaker(max_failures=1, drawdown_limit=0.1, cooldown_minutes=10)
    breaker.record_failure("connectivity")
    allowed, _ = breaker.can_trade(drawdown=0.0, connectivity_ok=False)
    assert allowed is False
    breaker.manual_override(minutes=5)
    allowed, reason = breaker.can_trade(drawdown=0.2, connectivity_ok=False)
    assert allowed is True
    assert reason == "manual_override"
