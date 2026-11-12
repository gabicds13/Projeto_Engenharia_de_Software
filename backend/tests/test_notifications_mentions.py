"""Testes do fluxo de menções com notificações mockadas, sem APIs externas."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.chat.mentions import extract_mentions
from app.clients.notifications_client import MockNotificationsClient
from app.core.security import CurrentUser, Role
from app.domain.schemas import Notification, NotificationScope, Priority, Source


def _user(user_id: str, project_ids: tuple[str, ...] = ("proj-123",)) -> CurrentUser:
    return CurrentUser(user_id=user_id, role=Role.DEV, project_ids=project_ids)


def _mention(recipient: str, event_id: str | None = None) -> Notification:
    return Notification(
        id=str(uuid4()),
        event_id=event_id or str(uuid4()),
        source=Source.CHAT,
        type="chat.mention",
        priority=Priority.MEDIUM,
        relevance_score=0.7,
        reason="Você foi mencionado em uma mensagem do Chat.",
        classified_by="rules",
        scope=NotificationScope.PROJECT,
        project_id="proj-123",
        target_user_id=recipient,
        title="Você foi mencionado no Chat",
        body="@user-b: mensagem de teste",
        link="/chat",
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_mention_is_visible_only_to_its_recipient():
    client = MockNotificationsClient()
    sent = await client.publish(_mention("user-b"))

    bob = await client.list(_user("user-b"), cursor=None, priority=None,
                            source=None, status=None, limit=100)
    alice = await client.list(_user("user-a"), cursor=None, priority=None,
                              source=None, status=None, limit=100)
    outside = await client.list(_user("user-b", ("another-project",)),
                                cursor=None, priority=None, source=None,
                                status=None, limit=100)

    assert sent.id in {item.id for item in bob.items}
    assert sent.id not in {item.id for item in alice.items}
    assert sent.id not in {item.id for item in outside.items}


@pytest.mark.asyncio
async def test_marking_as_read_is_per_user():
    client = MockNotificationsClient()
    original = (await client.list(_user("user-a"), cursor=None, priority=None,
                                  source=None, status=None, limit=100)).items[0]
    await client.mark_read(_user("user-a"), original.id)

    alice = await client.list(_user("user-a"), cursor=None, priority=None,
                              source=None, status=None, limit=100)
    bob = await client.list(_user("user-b"), cursor=None, priority=None,
                            source=None, status=None, limit=100)

    assert next(n for n in alice.items if n.id == original.id).read_at is not None
    assert next(n for n in bob.items if n.id == original.id).read_at is None


@pytest.mark.asyncio
async def test_duplicate_event_is_saved_only_once():
    client = MockNotificationsClient()
    await client.publish(_mention("user-b", event_id="mention-42"))
    await client.publish(_mention("user-b", event_id="mention-42"))

    page = await client.list(_user("user-b"), cursor=None, priority=None,
                             source=None, status=None, limit=100)
    assert sum(n.event_id == "mention-42" for n in page.items) == 1


@pytest.mark.asyncio
async def test_mention_reaches_recipient_over_websocket_source():
    client = MockNotificationsClient()
    source = client.ws_source(_user("user-b"))
    pending = asyncio.create_task(anext(source))
    await asyncio.sleep(0)

    notification = _mention("user-b")
    await client.publish(notification)
    received = await asyncio.wait_for(pending, timeout=1)
    assert received["event"] == "notification.new"
    assert received["data"]["id"] == notification.id
    await source.aclose()


def test_extract_mentions_without_duplicate_or_self_notification():
    assert extract_mentions(
        "Oi @user-b, pode ver? @user-b e @user-a",
        author_id="user-a",
    ) == {"user-b"}
