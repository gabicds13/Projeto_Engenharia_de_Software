"""Testes da rota de notificações (Requisitos 3.1, 3.5, 3.6)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

import app.clients as clients
import app.core.resilience as resilience
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Garante client e cache limpos entre testes (singletons com lru_cache)."""
    clients.get_notifications_client.cache_clear()
    resilience.get_registry.cache_clear()
    yield
    clients.get_notifications_client.cache_clear()
    resilience.get_registry.cache_clear()


def _token() -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "user-1",
            "role": "DEV",
            "project_ids": ["proj-123"],
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        s.jwt_secret,
        algorithm=s.jwt_algorithm,
    )


def _auth():
    return {"Authorization": f"Bearer {_token()}"}


def test_list_requires_auth(client):
    assert client.get("/api/bff/notifications").status_code == 401


def test_list_returns_notifications(client):
    r = client.get("/api/bff/notifications", headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "ok"
    assert len(body["page"]["items"]) == 4


def test_list_filter_by_priority(client):
    r = client.get(
        "/api/bff/notifications", params={"priority": "critical"}, headers=_auth()
    )
    assert r.status_code == 200
    items = r.json()["page"]["items"]
    assert all(n["priority"] == "critical" for n in items)


def test_unread_then_mark_all(client):
    before = client.get("/api/bff/notifications/unread-count", headers=_auth()).json()
    assert before["count"]["total"] == 4

    assert client.post("/api/bff/notifications/read-all", headers=_auth()).status_code == 200

    after = client.get("/api/bff/notifications/unread-count", headers=_auth()).json()
    assert after["count"]["total"] == 0


def test_mark_single_read(client):
    page = client.get("/api/bff/notifications", headers=_auth()).json()["page"]
    first_id = page["items"][0]["id"]
    assert client.patch(f"/api/bff/notifications/{first_id}", headers=_auth()).status_code == 200
    after = client.get("/api/bff/notifications/unread-count", headers=_auth()).json()
    assert after["count"]["total"] == 3


def test_upstream_unavailable_returns_state(client, monkeypatch):
    class Broken:
        async def list(self, *a, **k):
            raise RuntimeError("ms-notifications fora do ar")

    import app.notifications.router as nrouter

    monkeypatch.setattr(nrouter, "get_notifications_client", lambda: Broken())
    r = client.get("/api/bff/notifications", headers=_auth())
    assert r.status_code == 200
    assert r.json()["state"] == "unavailable"


def test_ws_rejects_without_token(client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/notifications"):
            pass


def test_ws_streams_with_valid_token(client, monkeypatch):
    import app.notifications.router as nrouter

    class FastSource:
        def __init__(self):
            self._user = None

        async def ws_source(self, user):
            yield {"event": "notification.new", "data": {"id": "ntf-x"}}

    monkeypatch.setattr(nrouter, "get_notifications_client", lambda: FastSource())
    with client.websocket_connect(f"/ws/notifications?token={_token()}") as ws:
        msg = ws.receive_json()
        assert msg["event"] == "notification.new"
