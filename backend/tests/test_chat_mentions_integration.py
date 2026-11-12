"""Testes de ponta a ponta das menções: rota HTTP, SQLite e feed em tempo real.

Simula duas contas do mesmo projeto sem acessar o Neon ou o Módulo 1.
O chat usa um cliente de memória; notificações usam o cliente real de banco.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clients.chat_client import MockChatClient
from app.clients.database_notifications_client import DatabaseNotificationsClient
from app.core.database import Base
from app.core.resilience import ResilienceRegistry
from app.core.security import CurrentUser, Role, get_current_user
from app.main import create_app
from app.models.notification import NotificationModel
from app.models.notification_read import NotificationReadModel  # noqa: F401


PROJECT = "proj-mentions"


@pytest.fixture
def scenario(monkeypatch):
    """Isola todos os registros em um SQLite temporário, sem DATABASE_URL."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )

    monkeypatch.setattr(
        "app.clients.database_notifications_client.get_session_factory",
        lambda: session_factory,
    )
    notifications = DatabaseNotificationsClient()
    chat = MockChatClient()

    monkeypatch.setattr("app.chat.router.get_chat_client", lambda: chat)
    monkeypatch.setattr(
        "app.chat.router.get_notifications_client", lambda: notifications
    )
    monkeypatch.setattr(
        "app.notifications.router.get_notifications_client",
        lambda: notifications,
    )

    # Não compartilhar cache de testes nem fazer chamadas aos outros módulos.
    registry = ResilienceRegistry(
        timeout_seconds=5,
        fails_to_open=3,
        reset_seconds=5,
        cache_ttl_seconds=10,
    )
    monkeypatch.setattr("app.notifications.router.get_registry", lambda: registry)

    state = {"user_id": "alice", "projects": (PROJECT,)}

    def logged_user():
        return CurrentUser(
            user_id=state["user_id"],
            role=Role.DEV,
            project_ids=state["projects"],
        )

    app = create_app()
    app.dependency_overrides[get_current_user] = logged_user
    try:
        with TestClient(app) as client:
            yield client, state, notifications, session_factory
    finally:
        engine.dispose()


def _switch(state, user_id, projects=(PROJECT,)):
    state["user_id"] = user_id
    state["projects"] = projects


def _feed(client):
    response = client.get("/api/bff/notifications")
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "ok"
    return response.json()["page"]["items"]


def _count(client):
    response = client.get("/api/bff/notifications/unread-count")
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "ok"
    return response.json()["count"]["total"]


def _send(client, text):
    response = client.post(
        f"/api/bff/chat/rooms/{PROJECT}/messages",
        json={"content": text},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_mencao_cria_uma_notificacao_apenas_para_destinatario(scenario):
    client, state, _, session_factory = scenario

    _switch(state, "alice")
    sent = _send(client, "Oi @bob, veja isso! @bob e @alice")
    assert sent["author_id"] == "alice"

    # A duplicação de @bob na mesma mensagem não gera alerta duplicado.
    _switch(state, "bob")
    alerts = _feed(client)
    assert len(alerts) == 1
    assert alerts[0]["type"] == "chat.mention"
    assert alerts[0]["target_user_id"] == "bob"
    assert alerts[0]["project_id"] == PROJECT
    assert alerts[0]["source"] == "chat"
    assert _count(client) == 1

    with session_factory() as db:
        saved = db.scalars(select(NotificationModel)).all()
        assert len(saved) == 1
        assert saved[0].event_id == f"chat-mention-{sent['id']}-bob"

    _switch(state, "alice")
    assert _feed(client) == []
    assert _count(client) == 0

    # Outra pessoa do mesmo projeto não pode consultar alerta privado.
    _switch(state, "carol")
    assert _feed(client) == []
    assert _count(client) == 0

    # Nem mesmo Bob pode vê-lo se estiver fora do projeto.
    _switch(state, "bob", projects=("outro-projeto",))
    assert _feed(client) == []
    assert _count(client) == 0


def test_mencao_propria_leitura_e_resposta_entre_usuarios(scenario):
    client, state, _, _ = scenario

    _switch(state, "alice")
    _send(client, "Mensagem só para @alice: não notificar.")
    assert _feed(client) == []
    assert _count(client) == 0

    _send(client, "Alô @bob! Pode responder?")
    _switch(state, "bob")
    alert = _feed(client)[0]
    assert _count(client) == 1

    read = client.patch(f"/api/bff/notifications/{alert['id']}")
    assert read.status_code == 200
    assert _count(client) == 0
    assert _feed(client)[0]["read_at"] is not None

    # A resposta de Bob gera alerta para Alice, sem reabrir o de Bob.
    _send(client, "Obrigado @alice!")
    assert _count(client) == 0
    _switch(state, "alice")
    alerts = _feed(client)
    assert len(alerts) == 1
    assert alerts[0]["target_user_id"] == "alice"
    assert _count(client) == 1


def test_usuario_fora_do_projeto_nao_consegue_gerar_mencoes(scenario):
    client, state, _, session_factory = scenario
    _switch(state, "alice", projects=("outro-projeto",))
    response = client.post(
        f"/api/bff/chat/rooms/{PROJECT}/messages",
        json={"content": "Oi @bob"},
    )
    assert response.status_code == 403
    with session_factory() as db:
        assert db.scalars(select(NotificationModel)).all() == []


@pytest.mark.asyncio
async def test_mencao_do_chat_chega_ao_stream_de_notificacoes(scenario):
    client, state, notifications, _ = scenario
    bob = CurrentUser(user_id="bob", role=Role.DEV, project_ids=(PROJECT,))
    stream = notifications.ws_source(bob)
    pending = asyncio.create_task(anext(stream))

    try:
        # Aguarda o stream inicializar antes de gerar uma mensagem.
        await asyncio.sleep(0.05)
        _switch(state, "alice")
        sent = _send(client, "Notificação em tempo real para @bob")
        event = await asyncio.wait_for(pending, timeout=6)
        assert event["event"] == "notification.new"
        assert event["data"]["target_user_id"] == "bob"
        assert event["data"]["type"] == "chat.mention"
        assert event["data"]["event_id"] == f"chat-mention-{sent['id']}-bob"
    finally:
        if not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        await stream.aclose()
