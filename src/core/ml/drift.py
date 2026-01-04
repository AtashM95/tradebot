from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DriftReport:
    data_drift: float
    performance_drift: float
    triggered: bool


@dataclass
class DriftMonitor:
    data_threshold: float
    performance_threshold: float

    def check(self, data_drift: float, performance_drift: float) -> DriftReport:
        triggered = data_drift > self.data_threshold or performance_drift > self.performance_threshold
        return DriftReport(data_drift=data_drift, performance_drift=performance_drift, triggered=triggered)
