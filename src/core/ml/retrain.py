from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import pickle
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.core.ml.registry import ModelRegistry


@dataclass
class RetrainPlan:
    reason: str
    triggered: bool


@dataclass
class RetrainResult:
    model_id: str
    model_path: str
    metrics: Dict[str, float]
    algorithm: str


@dataclass
class RetrainPipeline:
    schedule: str

    def plan(self, reason: str) -> RetrainPlan:
        return RetrainPlan(reason=reason, triggered=True)

    def run(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        registry_dir: str,
        feature_list: Optional[List[str]] = None,
        algorithm: str = "logistic_regression",
    ) -> RetrainResult:
        model, used_algorithm = _train_model(features, target, algorithm)
        metrics = _evaluate_model(model, features, target)
        model_id = f"model-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        registry = ModelRegistry(base_dir=Path(registry_dir))
        model_path = _save_model(registry.base_dir, model_id, model)
        registry.register_model(
            model_id=model_id,
            artifact_path=model_path,
            metrics=metrics,
            feature_list=feature_list or list(features.columns),
            algorithm=used_algorithm,
            set_active=True,
        )
        return RetrainResult(model_id=model_id, model_path=model_path, metrics=metrics, algorithm=used_algorithm)


def _save_model(base_dir: Path, model_id: str, model: Any) -> str:
    artifact_path = base_dir / f"{model_id}.pkl"
    with artifact_path.open("wb") as f:
        pickle.dump(model, f)
    return str(artifact_path)


def _train_model(features: pd.DataFrame, target: pd.Series, algorithm: str) -> Tuple[Any, str]:
    try:
        from sklearn.linear_model import LogisticRegression

        model = LogisticRegression(max_iter=500)
        model.fit(features, target)
        return model, "logistic_regression"
    except Exception:  # noqa: BLE001
        threshold = float(features.sum(axis=1).median())
        model = {"threshold": threshold}
        return model, "rule_based"


def _predict(model: Any, features: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict"):
        return model.predict(features)
    scores = features.sum(axis=1).to_numpy()
    return (scores >= model["threshold"]).astype(int)


def _evaluate_model(model: Any, features: pd.DataFrame, target: pd.Series) -> Dict[str, float]:
    preds = _predict(model, features)
    target_values = target.to_numpy()
    accuracy = float((preds == target_values).mean())
    precision = _safe_div((preds & target_values).sum(), preds.sum())
    recall = _safe_div((preds & target_values).sum(), target_values.sum())
    f1 = _safe_div(2 * precision * recall, precision + recall) if precision + recall > 0 else 0.0
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)
