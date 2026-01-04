from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.core.contracts import Features, SignalIntent


@dataclass(frozen=True)
class Strategy:
    name: str
    required_features: List[str]

    def generate(self, features: Features) -> SignalIntent | None:
        raise NotImplementedError
