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


def test_dashboard_reviews_completed_uses_real_m4_project(client, monkeypatch):
    from types import SimpleNamespace
    from app.dashboard import router as dashboard_router
    project = "f092329c-0747-4b88-92f0-c3036786ce91"
    settings = get_settings()
    monkeypatch.setattr(settings, "code_review_enabled", True)
    calls = []

    async def fake_metrics(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(total_revisoes=2)

    monkeypatch.setattr(dashboard_router, "fetch_code_review_metrics", fake_metrics)
    headers = {"Authorization": f"Bearer {_token(project_ids=(project,))}"}
    response = client.get("/api/bff/dashboard", params={"project_id": project}, headers=headers)
    assert response.status_code == 200
    cards = {card["key"]: card for card in response.json()["cards"]}
    assert cards["reviews_completed"]["value"] == 2
    assert cards["reviews_completed"]["data_origin"] == "real"
    assert cards["reviews_completed"]["state"] == "ok"
    assert "reviews_pending" not in cards
    assert calls == [{
        "base_url": settings.code_review_url, "project_id": project,
        "days": 14, "timeout": settings.code_review_timeout_seconds,
    }]
    denied = client.get("/api/bff/dashboard", params={"project_id": "other"}, headers=headers)
    assert denied.status_code == 403
    assert len(calls) == 1
