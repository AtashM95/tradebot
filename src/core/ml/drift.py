from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.util import find_spec
import sys
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class DriftReport:
    data_drift: float
    performance_drift: float
    triggered: bool
    drifted_features: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    method_used: str = "unknown"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DriftMonitor:
    data_threshold: float
    performance_threshold: float

    def check(self, data_drift: float, performance_drift: float) -> DriftReport:
        triggered = data_drift > self.data_threshold or performance_drift > self.performance_threshold
        return DriftReport(data_drift=data_drift, performance_drift=performance_drift, triggered=triggered)


def detect_drift(baseline_df: pd.DataFrame, current_df: pd.DataFrame, alpha: float = 0.05) -> DriftReport:
    if baseline_df.empty or current_df.empty:
        return DriftReport(data_drift=0.0, performance_drift=0.0, triggered=False, method_used="empty")
    numeric_cols = baseline_df.select_dtypes(include=[np.number]).columns.intersection(
        current_df.select_dtypes(include=[np.number]).columns
    )
    drifted_features: list[str] = []
    scores: dict[str, float] = {}
    method_used = "percentile_shift"
    scipy_available = sys.modules.get("scipy") is not None and find_spec("scipy") is not None
    if scipy_available:
        try:
            from scipy.stats import ks_2samp

            method_used = "ks_test"
            for col in numeric_cols:
                stat = ks_2samp(baseline_df[col].dropna(), current_df[col].dropna())
                score = 1 - stat.pvalue
                scores[col] = float(score)
                if stat.pvalue < alpha:
                    drifted_features.append(col)
        except Exception:  # noqa: BLE001
            method_used = "percentile_shift"
            scipy_available = False
    if not scipy_available:
        for col in numeric_cols:
            base = baseline_df[col].dropna().to_numpy()
            curr = current_df[col].dropna().to_numpy()
            if base.size == 0 or curr.size == 0:
                continue
            base_median = np.median(base)
            curr_median = np.median(curr)
            base_std = np.std(base) or 1.0
            shift = abs(curr_median - base_median) / base_std
            scores[col] = float(shift)
            if shift > 0.5:
                drifted_features.append(col)
    data_drift = len(drifted_features) / max(len(numeric_cols), 1)
    report = DriftReport(
        data_drift=float(data_drift),
        performance_drift=0.0,
        triggered=data_drift > 0.0,
        drifted_features=drifted_features,
        scores=scores,
        method_used=method_used,
    )
    return report
