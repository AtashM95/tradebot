from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass
class DataCache:
    base_dir: str | Path
    compression: bool = False
    keep_last_bars: int = 300

    def __post_init__(self) -> None:
        self.base_path = Path(self.base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / "bars").mkdir(parents=True, exist_ok=True)

    def load_daily_bars(self, symbol: str, limit: int) -> Optional[pd.DataFrame]:
        base = self.base_path / "bars" / symbol
        gzip_path = base.with_suffix(".csv.gz")
        csv_path = base.with_suffix(".csv")
        if gzip_path.exists():
            df = pd.read_csv(gzip_path)
        elif csv_path.exists():
            df = pd.read_csv(csv_path)
        else:
            return None
        if limit:
            return df.tail(limit).reset_index(drop=True)
        return df

    def save_daily_bars(self, symbol: str, bars: pd.DataFrame) -> None:
        suffix = ".csv.gz" if self.compression else ".csv"
        path = (self.base_path / "bars" / symbol).with_suffix(suffix)
        trimmed = bars.tail(self.keep_last_bars).reset_index(drop=True)
        trimmed.to_csv(path, index=False, compression="gzip" if self.compression else None)
