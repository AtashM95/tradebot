import sys

import pandas as pd

from src.core.ml.drift import detect_drift


def test_detect_drift_flags_shift():
    baseline = pd.DataFrame({"feature": [1, 1, 1, 1, 1], "noise": [0, 1, 0, 1, 0]})
    current = pd.DataFrame({"feature": [10, 10, 9, 11, 10], "noise": [0, 1, 0, 1, 0]})
    report = detect_drift(baseline, current, alpha=0.05)
    assert "feature" in report.drifted_features
    assert report.scores["feature"] > 0


def test_detect_drift_without_scipy(monkeypatch):
    monkeypatch.setitem(sys.modules, "scipy", None)
    baseline = pd.DataFrame({"feature": [1, 1, 1, 1, 1]})
    current = pd.DataFrame({"feature": [2, 2, 2, 2, 2]})
    report = detect_drift(baseline, current, alpha=0.05)
    assert report.method_used == "percentile_shift"
