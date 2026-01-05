from src.core.contracts import SignalIntent
from src.core.ensemble.aggregator import EnsembleAggregator


def test_ensemble_aggregate():
    intents = [
        SignalIntent(
            symbol="AAPL",
            confidence=0.8,
            entry=100.0,
            stop=95.0,
            take_profit=110.0,
            reasons=["trend"],
            strategy="trend_following",
        ),
        SignalIntent(
            symbol="AAPL",
            confidence=0.7,
            entry=100.0,
            stop=95.0,
            take_profit=110.0,
            reasons=["volume"],
            strategy="volume_confirm",
        ),
    ]
    aggregator = EnsembleAggregator(min_score=0.6)
    final = aggregator.aggregate(intents)
    assert final is not None
    assert final.symbol == "AAPL"
    assert final.score >= 0.6
