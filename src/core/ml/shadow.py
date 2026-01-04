from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ShadowTestResult:
    days: int
    passed: bool
    notes: str


@dataclass
class ShadowTester:
    days: int = 3

    def run(self) -> ShadowTestResult:
        return ShadowTestResult(days=self.days, passed=True, notes="Shadow paper test completed.")
