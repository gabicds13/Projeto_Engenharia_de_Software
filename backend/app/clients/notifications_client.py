"""Client do ms-notifications: lista, contador, marcar lida e stream (WS)."""
from __future__ import annotations

import asyncio
import itertools
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Protocol

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
    def ws_source(self, user: CurrentUser) -> AsyncIterator[dict]: ...


# --- Exemplos determinísticos para a demo (um por origem, cobrindo prioridades) ---
def _seed_notifications() -> list[Notification]:
    now = datetime.now(timezone.utc)
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
    def __init__(self) -> None:
        self._items: list[Notification] = _seed_notifications()
        self._counter = itertools.count(len(self._items) + 1)

    def _visible(self, user: CurrentUser) -> list[Notification]:
        # No mock, todas as notificações pertencem ao usuário conectado.
        return list(self._items)

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
        items = sorted(items, key=lambda n: n.created_at, reverse=True)
        return NotificationPage(items=items[:limit], next_cursor=None)

    async def unread_count(self, user: CurrentUser) -> UnreadCount:
        unread = [n for n in self._visible(user) if n.read_at is None]
        count = UnreadCount(total=len(unread))
        for n in unread:
            setattr(count, n.priority.value, getattr(count, n.priority.value) + 1)
        return count

    async def mark_read(self, user: CurrentUser, notif_id: str) -> None:
        for n in self._items:
            if n.id == notif_id and n.read_at is None:
                idx = self._items.index(n)
                self._items[idx] = n.model_copy(
                    update={"read_at": datetime.now(timezone.utc)}
                )

    async def mark_all_read(self, user: CurrentUser) -> None:
        now = datetime.now(timezone.utc)
        self._items = [
            n if n.read_at else n.model_copy(update={"read_at": now}) for n in self._items
        ]

    async def ws_source(self, user: CurrentUser) -> AsyncIterator[dict]:
        """Emite uma nova notificação periodicamente, para demonstrar o tempo real."""
        samples = [
            (Source.RELATORIOS, "report.generated", Priority.LOW, "Relatório de qualidade gerado"),
            (Source.ARTEFATOS, "artifact.uploaded", Priority.MEDIUM, "Novo documento de requisitos"),
            (Source.CODE_REVIEW, "build.failed", Priority.CRITICAL, "Build quebrado em main"),
        ]
        cycle = itertools.cycle(samples)
        while True:
            await asyncio.sleep(12)
            src, typ, prio, title = next(cycle)
            n = Notification(
                id=f"ntf-{next(self._counter):03d}",
                source=src,
                type=typ,
                priority=prio,
                relevance_score=0.8 if prio == Priority.CRITICAL else 0.4,
                reason="Evento recebido em tempo real (demo).",
                classified_by="rules",
                project_id="proj-123",
                title=title,
                body="Notificação de exemplo emitida pelo mock.",
                link="/projects/proj-123",
                created_at=datetime.now(timezone.utc),
                read_at=None,
            )
            self._items.append(n)
            yield {"event": "notification.new", "data": n.model_dump(mode="json")}


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
            except Exception as exc:  # noqa: BLE001
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
