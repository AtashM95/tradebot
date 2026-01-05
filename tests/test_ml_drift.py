import pandas as pd

from src.core.ml.drift import detect_drift


def test_detect_drift_flags_shift():
    baseline = pd.DataFrame({"feature": [1, 1, 1, 1, 1], "noise": [0, 1, 0, 1, 0]})
    current = pd.DataFrame({"feature": [10, 10, 9, 11, 10], "noise": [0, 1, 0, 1, 0]})
    report = detect_drift(baseline, current, alpha=0.05)
    assert "feature" in report.drifted_features
    assert report.scores["feature"] > 0
