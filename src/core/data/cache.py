from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass
class DataCache:
    base_dir: str | Path
    compression: Optional[str] = None
    data_format: str = "parquet"

    def __post_init__(self) -> None:
        self.base_path = Path(self.base_dir).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / "bars").mkdir(parents=True, exist_ok=True)
        if self.data_format not in {"parquet", "csv"}:
            raise ValueError(f"Unsupported data cache format: {self.data_format}")

    def load_daily_bars(self, symbol: str, limit: int) -> Optional[pd.DataFrame]:
        path = self._resolve_path(symbol)
        if not path.exists():
            return None
        if path.suffix == ".parquet":
            try:
                df = pd.read_parquet(path)
            except (ImportError, ValueError) as exc:
                logging.getLogger(__name__).warning(
                    "Parquet engine unavailable, falling back to CSV for %s: %s",
                    symbol,
                    exc,
                )
                csv_path = path.with_suffix(".csv")
                if not csv_path.exists():
                    return None
                df = pd.read_csv(csv_path)
        else:
            df = pd.read_csv(path)
        if limit:
            return df.tail(limit).reset_index(drop=True)
        return df

    def save_daily_bars(self, symbol: str, bars: pd.DataFrame) -> None:
        path = self._resolve_path(symbol)
        if path.suffix == ".parquet":
            try:
                bars.to_parquet(path, index=False, compression=self.compression)
                return
            except (ImportError, ValueError) as exc:
                logging.getLogger(__name__).warning(
                    "Parquet engine unavailable, saving CSV for %s: %s",
                    symbol,
                    exc,
                )
                path = path.with_suffix(".csv")
        bars.to_csv(path, index=False)

    def _resolve_path(self, symbol: str) -> Path:
        ext = ".parquet" if self.data_format == "parquet" else ".csv"
        return self.base_path / "bars" / f"{symbol}{ext}"
