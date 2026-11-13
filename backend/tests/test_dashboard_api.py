"""Testes da rota do dashboard (Requisitos 4.1, 2.5)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import jwt

from app.core.config import get_settings


def _token(project_ids=("proj-123",), role="DEV") -> str:
    s = get_settings()
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": "user-1",
            "role": role,
            "project_ids": list(project_ids),
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        s.jwt_secret,
        algorithm=s.jwt_algorithm,
    )


def test_dashboard_requires_auth(client):
    r = client.get("/api/bff/dashboard", params={"project_id": "proj-123"})
    assert r.status_code == 401


def test_dashboard_returns_cards(client):
    r = client.get(
        "/api/bff/dashboard",
        params={"project_id": "proj-123"},
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["project_id"] == "proj-123"
    assert len(body["cards"]) == 4
    assert body["weekly"]["state"] == "ok"
    assert body["weekly"]["data_origin"] == "mock"
    origins = {card["key"]: card["data_origin"] for card in body["cards"]}
    assert origins["commits_week"] == "mock"
    assert origins["open_prs"] == "mock"
    assert origins["stories_by_status"] == "mock"


def test_dashboard_forbidden_for_other_project(client):
    r = client.get(
        "/api/bff/dashboard",
        params={"project_id": "proj-999"},
        headers={"Authorization": f"Bearer {_token(project_ids=('proj-123',))}"},
    )
    assert r.status_code == 403
