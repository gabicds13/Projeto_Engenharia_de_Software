"""Fluxo HTTP real de convites, usando SQLite e usuários autenticados simulados."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.errors import ForbiddenError
from app.core.security import CurrentUser, Role, get_current_user
from app.main import create_app
from app.models.chat_channel import ChatChannelModel  # noqa: F401
from app.models.chat_channel_member import ChatChannelMemberModel  # noqa: F401
from app.models.chat_channel_read import ChatChannelReadModel  # noqa: F401
from app.models.chat_message import ChatMessageModel  # noqa: F401


@pytest.fixture
def ctx(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    app = create_app()
    state = {"user": "alice", "project_ids": ("proj-123",)}

    def db_override():
        with Session(engine) as db:
            yield db

    def user_override():
        return CurrentUser(
            user_id=state["user"],
            role=Role.DEV,
            project_ids=state["project_ids"],
        )

    async def ensure_access(project_id, user, settings):
        if project_id not in user.project_ids:
            raise ForbiddenError("Usuário não participa deste projeto.")

    monkeypatch.setattr("app.chat.router.ensure_project_access", ensure_access)
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_current_user] = user_override

    with TestClient(app) as client:
        yield client, state
    engine.dispose()


def test_invitation_flow_waits_for_recipient(ctx):
    client, state = ctx
    path = "/api/bff/chat/rooms/proj-123/direct"
    response = client.post(path, json={"target_user_id": "bob"})
    assert response.status_code == 200
    channel_id = response.json()["id"]

    sender_channels = client.get(path).json()
    assert sender_channels[0]["pending"] is True
    assert sender_channels[0]["needs_my_acceptance"] is False

    # O remetente nao pode escrever antes que Bob aceite.
    send = client.post(
        f"{path}/{channel_id}/messages",
        json={"content": "Oi, Bob!"},
    )
    assert send.status_code == 403

    state["user"] = "bob"
    pending = client.get(path).json()
    assert pending[0]["needs_my_acceptance"] is True

    accepted = client.post(f"{path}/{channel_id}/accept")
    assert accepted.status_code == 200

    state["user"] = "alice"
    send = client.post(
        f"{path}/{channel_id}/messages",
        json={"content": "Oi, Bob!"},
    )
    assert send.status_code == 200

    state["user"] = "bob"
    history = client.get(f"{path}/{channel_id}/messages")
    assert history.status_code == 200
    assert history.json()[0]["content"] == "Oi, Bob!"


def test_invitation_cannot_be_accepted_outside_project(ctx):
    client, state = ctx
    path = "/api/bff/chat/rooms/proj-123/direct"
    response = client.post(path, json={"target_user_id": "bob"})
    channel_id = response.json()["id"]

    state["user"] = "bob"
    state["project_ids"] = ("proj-999",)
    denied = client.post(f"{path}/{channel_id}/accept")
    assert denied.status_code == 403

    state["project_ids"] = ("proj-123",)
    state["user"] = "charlie"
    denied = client.post(f"{path}/{channel_id}/accept")
    assert denied.status_code == 403
