from src.core.storage.db import SQLiteStore


def test_sqlite_store_repeated_calls(tmp_path):
    db_path = tmp_path / "store.db"
    store = SQLiteStore(f"sqlite:///{db_path}")
    for idx in range(3):
        store.add_log("INFO", f"ping-{idx}")
        logs = store.list_logs()
        assert logs
    store.set_watchlist(["AAPL", "MSFT"])
    assert store.get_watchlist() == ["AAPL", "MSFT"]
