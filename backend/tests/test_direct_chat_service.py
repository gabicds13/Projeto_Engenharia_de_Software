"""Testes de convite, acesso e persistência do chat privado sem APIs externas."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.chat.service import (
    accept_direct_invitation,
    get_channel_unread_count,
    get_direct_messages,
    get_or_create_direct_channel,
    has_pending_members,
    list_direct_channels,
    mark_channel_as_read,
    send_direct_message,
)
from app.core.database import Base
from app.core.errors import ForbiddenError, NotFoundError
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


def test_invitation_must_be_accepted_before_messages(db):
    channel = get_or_create_direct_channel(db, "alice", "bob", "proj-123")
    same = get_or_create_direct_channel(db, "bob", "alice", "proj-123")
    assert channel.id == same.id
    assert has_pending_members(db, channel.id)
    assert list_direct_channels(db, "bob", "proj-123")[0][0].id == channel.id

    with pytest.raises(ForbiddenError):
        send_direct_message(db, channel.id, "proj-123", "alice", "Oi!")
    with pytest.raises(ForbiddenError):
        get_direct_messages(db, channel.id, "proj-123", "bob")

    accepted = accept_direct_invitation(db, channel.id, "proj-123", "bob")
    assert accepted.id == channel.id
    assert not has_pending_members(db, channel.id)

    sent = send_direct_message(db, channel.id, "proj-123", "alice", "Oi, Bob!")
    messages = get_direct_messages(db, channel.id, "proj-123", "bob")
    assert [message.id for message in messages] == [sent.id]
    assert get_channel_unread_count(db, channel.id, "bob", "proj-123") == 1
    assert get_channel_unread_count(db, channel.id, "alice", "proj-123") == 0
    mark_channel_as_read(db, channel.id, "bob", "proj-123")
    assert get_channel_unread_count(db, channel.id, "bob", "proj-123") == 0


def test_stranger_cannot_accept_or_read_invitation(db):
    channel = get_or_create_direct_channel(db, "alice", "bob", "proj-123")
    with pytest.raises(ForbiddenError):
        accept_direct_invitation(db, channel.id, "proj-123", "charlie")
    with pytest.raises(ForbiddenError):
        get_direct_messages(db, channel.id, "proj-123", "charlie")
    with pytest.raises(ForbiddenError):
        send_direct_message(db, channel.id, "proj-123", "charlie", "Oi")
    with pytest.raises(ForbiddenError):
        get_channel_unread_count(db, channel.id, "charlie", "proj-123")


def test_channel_is_restricted_to_its_project(db):
    channel = get_or_create_direct_channel(db, "alice", "bob", "proj-123")
    with pytest.raises(NotFoundError):
        accept_direct_invitation(db, channel.id, "proj-456", "bob")
    with pytest.raises(NotFoundError):
        get_direct_messages(db, channel.id, "proj-456", "alice")
    with pytest.raises(NotFoundError):
        get_channel_unread_count(db, channel.id, "alice", "proj-456")
    assert list_direct_channels(db, "charlie", "proj-123") == []


def test_cannot_invite_oneself(db):
    with pytest.raises(ForbiddenError):
        get_or_create_direct_channel(db, "alice", "alice", "proj-123")
