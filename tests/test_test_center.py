from fastapi.testclient import TestClient

from src.app.main import build_test_center, create_app
from src.core.settings import load_settings


def test_test_center_checks():
    settings = load_settings()
    test_center = build_test_center(settings, use_mock=True)
    app = create_app(settings=settings, test_center=test_center, use_mock=True)
    client = TestClient(app)
    response = client.get("/api/test-center/checks")
    assert response.status_code == 200
    checks = response.json()
    assert len(checks) == 6
    for check in checks:
        assert check["status"] in {"pass", "fail", "warn"}
        assert "name" in check
        assert "message" in check
