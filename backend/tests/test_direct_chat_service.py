"""Testes do chat privado no banco sem depender das APIs dos outros módulos."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.chat.service import (
    get_channel_unread_count,
    get_direct_messages,
    get_or_create_direct_channel,
    list_direct_channels,
    mark_channel_as_read,
    send_direct_message,
)
from app.core.database import Base
from app.models.chat_channel import ChatChannelModel  # noqa: F401
from app.models.chat_channel_member import ChatChannelMemberModel  # noqa: F401
from app.models.chat_channel_read import ChatChannelReadModel  # noqa: F401
from app.models.chat_message import ChatMessageModel  # noqa: F401


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_direct_chat_saves_history_and_read_receipts_per_user(db):
    channel = get_or_create_direct_channel(db, "alice", "bob", "proj-123")
    same_channel = get_or_create_direct_channel(db, "bob", "alice", "proj-123")
    assert channel.id == same_channel.id

    sent = send_direct_message(db, channel.id, "proj-123", "alice", "Oi, Bob!")
    bob_messages = get_direct_messages(db, channel.id, "proj-123", "bob")
    assert len(bob_messages) == 1
    assert bob_messages[0].id == sent.id

    assert get_channel_unread_count(db, channel.id, "bob") == 1
    assert get_channel_unread_count(db, channel.id, "alice") == 0

    mark_channel_as_read(db, channel.id, "bob")
    assert get_channel_unread_count(db, channel.id, "bob") == 0


def test_non_member_cannot_read_private_chat(db):
    channel = get_or_create_direct_channel(db, "alice", "bob", "proj-123")
    with pytest.raises(PermissionError):
        get_direct_messages(db, channel.id, "proj-123", "charlie")
    with pytest.raises(PermissionError):
        send_direct_message(db, channel.id, "proj-123", "charlie", "Oi")


def test_direct_channels_are_isolated_by_project(db):
    first = get_or_create_direct_channel(db, "alice", "bob", "proj-123")
    other = get_or_create_direct_channel(db, "alice", "bob", "proj-456")
    assert first.id != other.id
    assert [item[0].id for item in list_direct_channels(db, "alice", "proj-123")] == [first.id]
    assert list_direct_channels(db, "charlie", "proj-123") == []
