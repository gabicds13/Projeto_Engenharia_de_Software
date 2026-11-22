"""Testes de API real com dependencia do Modulo 1 indisponivel."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app


def test_offline_requires_development():
    assert not Settings(app_env="production", module1_offline_demo=True).module1_offline_enabled


def test_projects_and_dashboard_use_backend_real(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("MODULE1_OFFLINE_DEMO", "true")
    monkeypatch.setenv("USE_MOCKS", "true")
    monkeypatch.setenv("USE_CHAT_DB", "false")
    monkeypatch.setenv("USE_NOTIFICATIONS_DB", "false")
    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        assert client.get("/api/bff/projects").status_code == 401
        tokens = client.get("/api/bff/dev/tokens")
        assert tokens.status_code == 200
        bearer = tokens.json()["pm"]
        headers = {"Authorization": f"Bearer {bearer}"}
        projects = client.get("/api/bff/projects", headers=headers)
        assert projects.status_code == 200
        assert [p["project_id"] for p in projects.json()] == ["proj-123", "proj-456"]
        dashboard = client.get("/api/bff/dashboard", params={"project_id": "proj-123"}, headers=headers)
        assert dashboard.status_code == 200
        assert dashboard.json()["project_id"] == "proj-123"
        history = client.get("/api/bff/chat/rooms/proj-123/messages", headers=headers)
        assert history.status_code == 200
        denied = client.get("/api/bff/dashboard", params={"project_id": "outro-projeto"}, headers=headers)
        assert denied.status_code == 403
    finally:
        get_settings.cache_clear()
