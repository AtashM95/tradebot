from src.core.portfolio.trade_queue import TradeQueue
from src.core.storage.db import SQLiteStore


def test_trade_queue_enqueue(tmp_path):
    db_path = tmp_path / "test.db"
    store = SQLiteStore(f"sqlite:///{db_path}")
    queue = TradeQueue(store=store, ttl_hours=1)
    queue.enqueue("AAPL", {"symbol": "AAPL", "score": 0.8})
    items = queue.list_active()
    assert len(items) == 1
    assert items[0]["symbol"] == "AAPL"
