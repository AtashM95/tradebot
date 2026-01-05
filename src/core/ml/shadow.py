from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np


@dataclass
class ShadowTestResult:
    passed: bool
    details: Dict[str, float]
    metric_diff: float


@dataclass
class ShadowTester:
    days: int = 3

    def run(
        self,
        candidate_model: Any,
        active_model: Any,
        features: np.ndarray,
        target: np.ndarray,
        metric_name: str = "f1",
        delta: float = 0.01,
    ) -> ShadowTestResult:
        candidate_metrics = _evaluate(candidate_model, features, target)
        active_metrics = _evaluate(active_model, features, target)
        candidate_score = candidate_metrics.get(metric_name, 0.0)
        active_score = active_metrics.get(metric_name, 0.0)
        metric_diff = candidate_score - active_score
        passed = metric_diff >= delta
        details = {"candidate": candidate_score, "active": active_score}
        return ShadowTestResult(passed=passed, details=details, metric_diff=metric_diff)


def _predict(model: Any, features: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict"):
        return model.predict(features)
    scores = features.sum(axis=1)
    threshold = model.get("threshold", float(np.median(scores)))
    return (scores >= threshold).astype(int)


def _evaluate(model: Any, features: np.ndarray, target: np.ndarray) -> Dict[str, float]:
    preds = _predict(model, features)
    accuracy = float((preds == target).mean())
    precision = _safe_div((preds & target).sum(), preds.sum())
    recall = _safe_div((preds & target).sum(), target.sum())
    f1 = _safe_div(2 * precision * recall, precision + recall) if precision + recall > 0 else 0.0
    return {"accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1}


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)
