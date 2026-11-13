"""Testes da rota de chat (Requisitos 5.1, 5.2, 5.3, 5.4)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app import clients
from app.core import resilience
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
    now = datetime.now(UTC)
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

    with client.websocket_connect(
        "/ws/chat?project_id=proj-999"
    ) as ws:
        ws.send_json(
            {
                "type": "auth",
                "token": _token(("proj-123",)),
            }
        )

        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


def test_falha_de_notificacoes_nao_interrompe_mensagem_ja_salva(client, monkeypatch):
    import app.chat.router as chat_router

    class NotificationsOffline:
        async def publish(self, notification):
            raise ConnectionError("Serviço de notificações desligado")

    monkeypatch.setattr(
        chat_router, "get_notifications_client", lambda: NotificationsOffline()
    )

    message = client.post(
        "/api/bff/chat/rooms/proj-123/messages",
        json={"content": "Oi @pessoa-teste, mensagem persistida."},
        headers=_auth(),
    )
    assert message.status_code == 200, message.text
    saved = message.json()
    assert saved["content"] == "Oi @pessoa-teste, mensagem persistida."

    history = client.get(
        "/api/bff/chat/rooms/proj-123/messages", headers=_auth()
    )
    assert history.status_code == 200
    assert saved["id"] in {item["id"] for item in history.json()["messages"]}


def test_falha_ao_iniciar_cliente_de_notificacoes_nao_interrompe_chat(
    client, monkeypatch
):
    import app.chat.router as chat_router

    def broken_notifications_client():
        raise ConnectionError("Serviço de notificações indisponível")

    monkeypatch.setattr(
        chat_router, "get_notifications_client", broken_notifications_client
    )
    result = client.post(
        "/api/bff/chat/rooms/proj-123/messages",
        json={"content": "Oi @pessoa-teste, teste de recuperação."},
        headers=_auth(),
    )
    assert result.status_code == 200
    assert result.json()["content"] == "Oi @pessoa-teste, teste de recuperação."


def test_queda_notificacoes_nao_interrompe_dashboard(client, monkeypatch):
    import app.notifications.router as notifications_router

    class Offline:
        async def list(self, *args, **kwargs):
            raise ConnectionError("Notificações indisponíveis")

    monkeypatch.setattr(
        notifications_router, "get_notifications_client", lambda: Offline()
    )
    notifications = client.get("/api/bff/notifications", headers=_auth())
    assert notifications.status_code == 200
    assert notifications.json()["state"] == "unavailable"

    dashboard = client.get(
        "/api/bff/dashboard",
        params={"project_id": "proj-123"},
        headers=_auth(),
    )
    assert dashboard.status_code == 200
    assert len(dashboard.json()["cards"]) == 4
