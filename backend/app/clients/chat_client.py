"""Client do ms-chat: histórico, envio e stream (WS) por projeto."""
from __future__ import annotations

import asyncio
import itertools
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Protocol

import httpx

from app.clients.base import UpstreamError, raise_for_status
from app.core.security import CurrentUser, downstream_headers
from app.domain.schemas import ChatMessage


class ChatClient(Protocol):
    async def history(self, user: CurrentUser, project_id: str, *, limit: int) -> list[ChatMessage]: ...
    async def post(self, user: CurrentUser, project_id: str, text: str) -> ChatMessage: ...
    def ws_source(self, user: CurrentUser, project_id: str) -> AsyncIterator[dict]: ...


class MockChatClient:
    """Histórico em memória por projeto; ecoa mensagens enviadas aos ouvintes."""

    def __init__(self) -> None:
        self._messages: dict[str, list[ChatMessage]] = defaultdict(list)
        self._counter = itertools.count(1)
        self._listeners: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._seed()

    def _seed(self) -> None:
        now = datetime.now(timezone.utc)
        seed = [
            ("user-gabi", "Pessoal, subi o esqueleto do dashboard."),
            ("user-heloisa", "Boa! Já consigo consumir as notificações mockadas."),
            ("user-daniel", "O chat já está persistindo o histórico por projeto."),
        ]
        for i, (author, content) in enumerate(seed):
            self._messages["proj-123"].append(
                ChatMessage(
                    id=f"msg-{next(self._counter):03d}",
                    project_id="proj-123",
                    author_id=author,
                    content=content,
                    created_at=now - timedelta(minutes=10 - i),
                )
            )

    async def history(self, user: CurrentUser, project_id: str, *, limit: int = 50) -> list[ChatMessage]:
        msgs = self._messages.get(project_id, [])
        return msgs[-limit:]

    async def post(self, user: CurrentUser, project_id: str, text: str) -> ChatMessage:
        msg = ChatMessage(
            id=f"msg-{next(self._counter):03d}",
            project_id=project_id,
            author_id=user.user_id,
            content=text,
            created_at=datetime.now(timezone.utc),
        )
        self._messages[project_id].append(msg)
        for q in self._listeners[project_id]:
            q.put_nowait({"event": "chat.message", "data": msg.model_dump(mode="json")})
        return msg

    async def ws_source(self, user: CurrentUser, project_id: str) -> AsyncIterator[dict]:
        q: asyncio.Queue = asyncio.Queue()
        self._listeners[project_id].append(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._listeners[project_id].remove(q)


class HttpChatClient:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    async def history(self, user: CurrentUser, project_id: str, *, limit: int = 50) -> list[ChatMessage]:
        async with httpx.AsyncClient(headers=downstream_headers(user)) as c:
            r = raise_for_status(
                await c.get(
                    f"{self._base_url}/api/v1/rooms/{project_id}/messages",
                    params={"limit": limit},
                )
            )
            try:
                return [ChatMessage.model_validate(m) for m in r.json().get("messages", [])]
            except Exception as exc:  # noqa: BLE001
                raise UpstreamError(f"resposta inválida do chat: {exc}") from exc

    async def post(self, user: CurrentUser, project_id: str, text: str) -> ChatMessage:
        async with httpx.AsyncClient(headers=downstream_headers(user)) as c:
            r = raise_for_status(
                await c.post(
                    f"{self._base_url}/api/v1/rooms/{project_id}/messages",
                    json={"content": text},
                )
            )
            return ChatMessage.model_validate(r.json())

    async def ws_source(self, user: CurrentUser, project_id: str) -> AsyncIterator[dict]:  # pragma: no cover
        url = self._base_url.replace("http", "ws", 1) + f"/ws/chat?project_id={project_id}"
        async with httpx.AsyncClient() as c:
            async with c.stream("GET", url, headers=downstream_headers(user)) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        import json

                        yield json.loads(line)
