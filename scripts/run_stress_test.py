from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.core.data.alpaca_client import MockAlpacaClient
from src.core.data.cache import DataCache
from src.core.data.market_data import MarketDataProvider
from src.core.risk.stress_tester import StressTester
from src.core.settings import load_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run portfolio stress test scenarios.")
    parser.add_argument("--symbols", required=True, help="Comma-separated list of symbols.")
    parser.add_argument("--shock", type=float, required=True, help="Shock return (e.g. -0.1 for -10%).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    symbols = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]
    if not symbols:
        raise ValueError("At least one symbol required.")
    client = MockAlpacaClient()
    cache = DataCache(settings.storage.cache_dir)
    provider = MarketDataProvider(client=client, cache=cache)
    price_history: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        price_history[symbol] = provider.get_daily_bars(symbol, limit=120)
    weights = {symbol: 1.0 / len(symbols) for symbol in symbols}
    tester = StressTester()
    results = tester.run(price_history, weights, {"custom": args.shock})
    for result in results:
        print(f"Scenario: {result.scenario} -> Portfolio return {result.portfolio_return:.2%}")
        for symbol, impact in result.details.items():
            print(f"  {symbol}: {impact:.2%}")


if __name__ == "__main__":
    main()
