from pathlib import Path

import numpy as np
import pandas as pd

from src.core.ml.retrain import RetrainPipeline
from src.core.ml.shadow import ShadowTester


def test_retrain_creates_artifact_and_metrics(tmp_path: Path):
    features = pd.DataFrame({"x1": [0, 1, 2, 3, 4, 5], "x2": [1, 1, 0, 0, 1, 0]})
    target = pd.Series([0, 0, 0, 1, 1, 1])
    pipeline = RetrainPipeline(schedule="manual")
    result = pipeline.run(features, target, registry_dir=str(tmp_path))
    assert Path(result.model_path).exists()
    assert "accuracy" in result.metrics


def test_shadow_tester_compares_models():
    features = np.array([[0, 1], [1, 1], [2, 0], [3, 0]])
    target = np.array([0, 0, 1, 1])
    candidate = {"threshold": 2.5}
    active = {"threshold": 4.0}
    tester = ShadowTester(days=3)
    result = tester.run(candidate, active, features, target, metric_name="accuracy", delta=0.1)
    assert result.passed is True
    assert "candidate" in result.details
