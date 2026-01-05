import pandas as pd
import pytest

from src.core.data.validator import MarketDataValidator


def test_market_data_validator_rejects_missing_columns():
    df = pd.DataFrame({"ts": ["2024-01-01"], "open": [1], "high": [1], "low": [1], "close": [1]})
    validator = MarketDataValidator()
    with pytest.raises(ValueError, match="missing columns"):
        validator.preprocess(df)


def test_market_data_validator_fills_nan():
    df = pd.DataFrame(
        {
            "ts": ["2024-01-01", "2024-01-02"],
            "open": [1.0, 1.1],
            "high": [1.2, 1.3],
            "low": [0.9, 1.0],
            "close": [1.0, None],
            "volume": [100, 110],
        }
    )
    validator = MarketDataValidator()
    result = validator.preprocess(df)
    assert result["close"].isna().sum() == 0
