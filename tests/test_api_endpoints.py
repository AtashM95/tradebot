import pickle
from pathlib import Path

from fastapi.testclient import TestClient

from src.app.main import create_app
from src.core.ml.registry import ModelRegistry
from src.core.settings import Settings, StorageSettings


def _build_app(tmp_path: Path) -> TestClient:
    registry_dir = tmp_path / "registry"
    settings = Settings(
        storage=StorageSettings(database_url=f"sqlite:///{tmp_path / 'tradebot.db'}", cache_dir=str(tmp_path / "cache")),
        ml={"registry": {"directory": str(registry_dir)}},
        sector_map_path="config/sector_map.json",
    )
    app = create_app(settings=settings, use_mock=True)
    return TestClient(app)


def test_backtest_run_endpoint(tmp_path):
    client = _build_app(tmp_path)
    response = client.post("/api/backtest/run", json={"symbols": ["AAPL"], "years": 1})
    assert response.status_code == 200
    payload = response.json()
    assert "aggregate" in payload
    assert "equity_curve" in payload


def test_models_list_and_active(tmp_path):
    client = _build_app(tmp_path)
    registry_dir = Path(client.app.state.settings.ml.registry.directory)
    registry = ModelRegistry(base_dir=registry_dir)
    model_path = registry_dir / "model-test.pkl"
    with model_path.open("wb") as handle:
        pickle.dump({"threshold": 1.0}, handle)
    registry.register_model(
        model_id="model-test",
        artifact_path=str(model_path),
        metrics={"accuracy": 1.0},
        feature_list=["feature"],
        algorithm="rule_based",
        set_active=True,
    )
    model_path2 = registry_dir / "model-test-2.pkl"
    with model_path2.open("wb") as handle:
        pickle.dump({"threshold": 2.0}, handle)
    registry.register_model(
        model_id="model-test-2",
        artifact_path=str(model_path2),
        metrics={"accuracy": 0.9},
        feature_list=["feature"],
        algorithm="rule_based",
        set_active=False,
    )
    response = client.get("/api/models/list")
    assert response.status_code == 200
    assert response.json()
    response = client.get("/api/models/active")
    assert response.json().get("model_id") == "model-test"
    response = client.post("/api/models/set-active", json={"model_id": "model-test-2"})
    assert response.status_code == 200
    response = client.get("/api/models/active")
    assert response.json().get("model_id") == "model-test-2"


def test_analyze_all_endpoint(tmp_path):
    client = _build_app(tmp_path)
    client.post("/api/orchestrator/start")
    response = client.post("/api/analyze/all")
    assert response.status_code == 200
    payload = response.json()
    assert "processed" in payload


def test_watchlist_validation_allows_dot(tmp_path):
    client = _build_app(tmp_path)
    response = client.post("/api/watchlist", json={"symbols": "BRK.B AAPL"})
    assert response.status_code == 200
    payload = response.json()
    assert "BRK.B" in payload.get("symbols", [])
    bad_response = client.post("/api/watchlist", json={"symbols": "BAD$"})
    assert "error" in bad_response.json()
