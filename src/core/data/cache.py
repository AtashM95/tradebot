from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass
class DataCache:
    base_dir: str | Path
    compression: str | None = "zstd"
    keep_last_bars: int = 300

    def __post_init__(self) -> None:
        self.base_path = Path(self.base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / "bars").mkdir(parents=True, exist_ok=True)

    def load_daily_bars(self, symbol: str, limit: int) -> Optional[pd.DataFrame]:
        path = self.base_path / "bars" / f"{symbol}.parquet"
        if not path.exists():
            return None
        df = pd.read_parquet(path)
        if limit:
            return df.tail(limit).reset_index(drop=True)
        return df

    def save_daily_bars(self, symbol: str, bars: pd.DataFrame) -> None:
        path = self.base_path / "bars" / f"{symbol}.parquet"
        trimmed = bars.tail(self.keep_last_bars).reset_index(drop=True)
        trimmed.to_parquet(path, index=False, compression=self.compression)
