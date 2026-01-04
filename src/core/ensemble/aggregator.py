from __future__ import annotations

from dataclasses import dataclass

from src.core.contracts import FinalSignal, SignalIntent


@dataclass
class EnsembleAggregator:
    min_score: float = 0.7

    def aggregate(self, intents: list[SignalIntent]) -> FinalSignal | None:
        if not intents:
            return None
        score = sum(intent.confidence for intent in intents) / len(intents)
        if score < self.min_score:
            return None
        top = max(intents, key=lambda x: x.confidence)
        reasons = []
        for intent in intents:
            reasons.extend(intent.reasons)
        return FinalSignal(
            symbol=top.symbol,
            score=score,
            entry=top.entry,
            stop=top.stop,
            take_profit=top.take_profit,
            reasons=reasons,
            intents=intents,
        )
