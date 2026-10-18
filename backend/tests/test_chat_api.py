"""Testes da rota de chat (Requisitos 5.1, 5.2, 5.3, 5.4)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

import app.clients as clients
import app.core.resilience as resilience
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _reset_singletons():
    clients.get_chat_client.cache_clear()
    resilience.get_registry.cache_clear()
    yield
    clients.get_chat_client.cache_clear()
    resilience.get_registry.cache_clear()


def _token(project_ids=("proj-123",)) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "user-1",
            "role": "DEV",
            "project_ids": list(project_ids),
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        s.jwt_secret,
        algorithm=s.jwt_algorithm,
    )


def _auth(project_ids=("proj-123",)):
    return {"Authorization": f"Bearer {_token(project_ids)}"}


def test_history_requires_auth(client):
    assert client.get("/api/bff/chat/rooms/proj-123/messages").status_code == 401


def test_history_returns_messages(client):
    r = client.get("/api/bff/chat/rooms/proj-123/messages", headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "ok"
    assert len(body["messages"]) == 3


def test_post_message_appends_to_history(client):
    r = client.post(
        "/api/bff/chat/rooms/proj-123/messages",
        json={"content": "Olá, time!"},
        headers=_auth(),
    )
    assert r.status_code == 200
    assert r.json()["content"] == "Olá, time!"

    hist = client.get("/api/bff/chat/rooms/proj-123/messages", headers=_auth()).json()
    assert hist["messages"][-1]["content"] == "Olá, time!"


def test_access_denied_to_project_outside_token(client):
    r = client.get(
        "/api/bff/chat/rooms/proj-999/messages", headers=_auth(project_ids=("proj-123",))
    )
    assert r.status_code == 403


def test_empty_message_rejected(client):
    r = client.post(
        "/api/bff/chat/rooms/proj-123/messages", json={"content": ""}, headers=_auth()
    )
    assert r.status_code == 422


def test_ws_rejects_project_outside_token(client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/ws/chat?project_id=proj-999&token={_token(('proj-123',))}"
        ):
            pass
