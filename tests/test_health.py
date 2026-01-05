from fastapi.testclient import TestClient

from src.app.main import build_test_center, create_app
from src.core.settings import load_settings


def test_health_endpoint():
    settings = load_settings()
    test_center = build_test_center(settings, use_mock=True)
    app = create_app(settings=settings, test_center=test_center, use_mock=True)
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["uptime_seconds"] >= 0
