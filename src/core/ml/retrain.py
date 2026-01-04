from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetrainPlan:
    reason: str
    triggered: bool


@dataclass
class RetrainPipeline:
    schedule: str

    def plan(self, reason: str) -> RetrainPlan:
        return RetrainPlan(reason=reason, triggered=True)
