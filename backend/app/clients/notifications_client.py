"""Client do ms-notifications: lista, contador, marcar lida e stream (WS)."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Protocol

import httpx

from app.clients.base import UpstreamError, raise_for_status
from app.core.security import CurrentUser, downstream_headers
from app.domain.schemas import (
    Notification,
    NotificationPage,
    Priority,
    Source,
    UnreadCount,
)


class NotificationsClient(Protocol):
    async def list(
        self,
        user: CurrentUser,
        *,
        cursor: str | None,
        priority: Priority | None,
        source: Source | None,
        status: str | None,
        limit: int,
    ) -> NotificationPage: ...
    async def unread_count(self, user: CurrentUser) -> UnreadCount: ...
    async def mark_read(self, user: CurrentUser, notif_id: str) -> None: ...
    async def mark_all_read(self, user: CurrentUser) -> None: ...
    async def publish(self, notification: Notification) -> Notification: ...
    def ws_source(self, user: CurrentUser) -> AsyncIterator[dict]: ...


# --- Exemplos determinísticos para a demo (um por origem, cobrindo prioridades) ---
def _seed_notifications() -> list[Notification]:
    now = datetime.now(UTC)
    base = [
        dict(
            source=Source.CODE_REVIEW,
            type="review.critical_issue.found",
            priority=Priority.CRITICAL,
            relevance_score=0.96,
            reason="Você é o autor do PR e o problema é de segurança.",
            classified_by="llm",
            title="Vulnerabilidade crítica no PR #42",
            body="Credencial exposta em config/settings.py no PR #42.",
            link="/projects/proj-123/reviews/42",
        ),
        dict(
            source=Source.GITHUB,
            type="github.pull_request.stale",
            priority=Priority.HIGH,
            relevance_score=0.74,
            reason="PR bloqueando a sprint atual e sem revisão há 3 dias.",
            classified_by="rules",
            title="PR #38 aguardando revisão há 3 dias",
            body="Bloqueia a US-12 da sprint atual.",
            link="/projects/proj-123/pulls/38",
        ),
        dict(
            source=Source.GITHUB,
            type="github.pr.comment",
            priority=Priority.MEDIUM,
            relevance_score=0.5,
            reason="Comentário em PR que você acompanha.",
            classified_by="rules",
            title="Novo comentário no PR #40",
            body="Revisor sugeriu extrair um método em auth/service.py.",
            link="/projects/proj-123/pulls/40",
        ),
        dict(
            source=Source.CURADORIA,
            type="curation.item.recommended",
            priority=Priority.LOW,
            relevance_score=0.2,
            reason="Novidade relevante para a stack do projeto.",
            classified_by="rules",
            title="FastAPI 0.120 lançado",
            body="Inclui melhorias de validação relevantes para a stack.",
            link="/projects/proj-123/curation/1",
        ),
    ]
    out: list[Notification] = []
    for i, item in enumerate(base):
        out.append(
            Notification(
                id=f"ntf-{i + 1:03d}",
                project_id="proj-123",
                created_at=now - timedelta(minutes=5 * (i + 1)),
                read_at=None,
                **item,
            )
        )
    return out


class MockNotificationsClient:
    """Notificações de demonstração com isolamento por usuário e entrega em tempo real.

    Não depende das APIs de outros módulos. Novos eventos chegam pelo endpoint
    POST /api/integrations/notifications, que já existe no projeto.
    """

    def __init__(self) -> None:
        self._items: list[Notification] = _seed_notifications()
        self._reads: dict[str, dict[str, datetime]] = {}
        self._subscribers: list[tuple[CurrentUser, asyncio.Queue[Notification]]] = []

    def _visible(self, user: CurrentUser) -> list[Notification]:
        reads = self._reads.get(user.user_id, {})
        return [
            item.model_copy(update={"read_at": reads.get(item.id, item.read_at)})
            for item in self._items
            if (item.scope.value == "global" or item.project_id in user.project_ids)
            and (item.target_user_id is None or item.target_user_id == user.user_id)
        ]

    async def list(
        self,
        user: CurrentUser,
        *,
        cursor: str | None = None,
        priority: Priority | None = None,
        source: Source | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> NotificationPage:
        items = self._visible(user)
        if priority is not None:
            items = [n for n in items if n.priority == priority]
        if source is not None:
            items = [n for n in items if n.source == source]
        if status == "unread":
            items = [n for n in items if n.read_at is None]
        elif status == "read":
            items = [n for n in items if n.read_at is not None]
        items.sort(key=lambda n: n.created_at, reverse=True)
        return NotificationPage(items=items[:limit], next_cursor=None)

    async def unread_count(self, user: CurrentUser) -> UnreadCount:
        unread = [n for n in self._visible(user) if n.read_at is None]
        count = UnreadCount(total=len(unread))
        for n in unread:
            setattr(count, n.priority.value, getattr(count, n.priority.value) + 1)
        return count

    async def mark_read(self, user: CurrentUser, notif_id: str) -> None:
        if any(n.id == notif_id for n in self._visible(user)):
            self._reads.setdefault(user.user_id, {}).setdefault(
                notif_id, datetime.now(UTC)
            )

    async def mark_all_read(self, user: CurrentUser) -> None:
        reads = self._reads.setdefault(user.user_id, {})
        now = datetime.now(UTC)
        for item in self._visible(user):
            reads.setdefault(item.id, now)

    async def publish(self, notification: Notification) -> Notification:
        if notification.event_id:
            for item in self._items:
                if item.event_id == notification.event_id:
                    return item

        self._items.append(notification)
        for subscriber, queue in list(self._subscribers):
            if any(item.id == notification.id for item in self._visible(subscriber)):
                queue.put_nowait(notification)
        return notification

    async def ws_source(self, user: CurrentUser) -> AsyncIterator[dict]:
        """Publica eventos novos; não fabrica notificações a cada conexão."""
        queue: asyncio.Queue[Notification] = asyncio.Queue()
        subscription = (user, queue)
        self._subscribers.append(subscription)
        try:
            while True:
                notification = await queue.get()
                yield {
                    "event": "notification.new",
                    "data": notification.model_dump(mode="json"),
                }
        finally:
            if subscription in self._subscribers:
                self._subscribers.remove(subscription)


class HttpNotificationsClient:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    async def list(
        self,
        user: CurrentUser,
        *,
        cursor: str | None = None,
        priority: Priority | None = None,
        source: Source | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> NotificationPage:
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        if priority:
            params["priority"] = priority.value
        if source:
            params["source"] = source.value
        if status:
            params["status"] = status
        async with httpx.AsyncClient(headers=downstream_headers(user)) as c:
            r = raise_for_status(
                await c.get(f"{self._base_url}/api/v1/notifications", params=params)
            )
            try:
                return NotificationPage.model_validate(r.json())
            except Exception as exc:
                raise UpstreamError(f"resposta inválida de notifications: {exc}") from exc

    async def unread_count(self, user: CurrentUser) -> UnreadCount:
        async with httpx.AsyncClient(headers=downstream_headers(user)) as c:
            r = raise_for_status(
                await c.get(f"{self._base_url}/api/v1/notifications/unread-count")
            )
            return UnreadCount.model_validate(r.json())

    async def mark_read(self, user: CurrentUser, notif_id: str) -> None:
        async with httpx.AsyncClient(headers=downstream_headers(user)) as c:
            raise_for_status(
                await c.patch(
                    f"{self._base_url}/api/v1/notifications/{notif_id}",
                    json={"read": True},
                )
            )

    async def mark_all_read(self, user: CurrentUser) -> None:
        async with httpx.AsyncClient(headers=downstream_headers(user)) as c:
            raise_for_status(
                await c.post(f"{self._base_url}/api/v1/notifications/read-all")
            )

    async def ws_source(self, user: CurrentUser) -> AsyncIterator[dict]:
        url = self._base_url.replace("http", "ws", 1) + "/ws/notifications"
        async with httpx.AsyncClient() as c:  # pragma: no cover - integração real
            async with c.stream("GET", url, headers=downstream_headers(user)) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        import json

                        yield json.loads(line)
