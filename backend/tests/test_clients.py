"""Testes dos clients mock (Requisitos 4.2, 3.1, 3.5, 5.2, 5.3)."""
from __future__ import annotations

from app.clients.backlog_client import MockBacklogClient
from app.clients.chat_client import MockChatClient
from app.clients.github_client import MockGithubClient
from app.clients.notifications_client import MockNotificationsClient
from app.core.security import CurrentUser, Role
from app.domain.schemas import Priority, Source

USER = CurrentUser(user_id="user-1", role=Role.DEV, project_ids=("proj-123",))


async def test_backlog_mock_values():
    c = MockBacklogClient()
    stories = await c.stories_by_status("proj-123")
    assert stories.done == 14
    assert await c.reviews_pending("proj-123") == 3


async def test_github_mock_values():
    c = MockGithubClient()
    series = await c.weekly_commits_prs("proj-123")
    assert len(series.points) == 5
    assert await c.open_prs("proj-123") == 7
    assert await c.commits_this_week("proj-123") == 47


async def test_notifications_list_and_filters():
    c = MockNotificationsClient()
    page = await c.list(USER, cursor=None, priority=None, source=None, status=None, limit=20)
    assert len(page.items) == 4
    # ordenado por created_at desc
    assert page.items[0].created_at >= page.items[-1].created_at

    only_critical = await c.list(
        USER, cursor=None, priority=Priority.CRITICAL, source=None, status=None, limit=20
    )
    assert all(n.priority == Priority.CRITICAL for n in only_critical.items)

    only_github = await c.list(
        USER, cursor=None, priority=None, source=Source.GITHUB, status=None, limit=20
    )
    assert all(n.source == Source.GITHUB for n in only_github.items)


async def test_notifications_unread_and_mark_read():
    c = MockNotificationsClient()
    before = await c.unread_count(USER)
    assert before.total == 4

    first = (await c.list(USER, cursor=None, priority=None, source=None, status=None, limit=1)).items[0]
    await c.mark_read(USER, first.id)
    after = await c.unread_count(USER)
    assert after.total == 3

    await c.mark_all_read(USER)
    assert (await c.unread_count(USER)).total == 0


async def test_chat_history_and_post():
    c = MockChatClient()
    hist = await c.history(USER, "proj-123", limit=50)
    assert len(hist) == 3

    msg = await c.post(USER, "proj-123", "Olá, time!")
    assert msg.author_id == "user-1"
    assert msg.content == "Olá, time!"

    hist2 = await c.history(USER, "proj-123", limit=50)
    assert hist2[-1].content == "Olá, time!"
