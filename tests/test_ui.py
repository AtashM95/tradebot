from fastapi.testclient import TestClient

from src.app.main import create_app


def test_dashboard_renders_with_i18n():
    app = create_app()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "window.I18N" in response.text
