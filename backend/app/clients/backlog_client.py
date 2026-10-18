"""Client do Módulo 1 (Auth/Backlog): User Stories e reviews pendentes."""
from __future__ import annotations

from typing import Protocol

import httpx

from app.clients.base import UpstreamError, raise_for_status
from app.domain.schemas import StoriesByStatus


class BacklogClient(Protocol):
    async def stories_by_status(self, project_id: str) -> StoriesByStatus: ...
    async def reviews_pending(self, project_id: str) -> int: ...


class MockBacklogClient:
    """Dados determinísticos para a demo (números estáveis entre chamadas)."""

    async def stories_by_status(self, project_id: str) -> StoriesByStatus:
        return StoriesByStatus(todo=8, in_progress=5, in_review=3, done=14)

    async def reviews_pending(self, project_id: str) -> int:
        return 3


class HttpBacklogClient:
    def __init__(self, base_url: str, headers: dict[str, str] | None = None):
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}

    async def stories_by_status(self, project_id: str) -> StoriesByStatus:
        async with httpx.AsyncClient(headers=self._headers) as c:
            r = raise_for_status(
                await c.get(f"{self._base_url}/api/v1/projects/{project_id}/stories/summary")
            )
            try:
                return StoriesByStatus.model_validate(r.json())
            except Exception as exc:  # noqa: BLE001
                raise UpstreamError(f"resposta inválida do backlog: {exc}") from exc

    async def reviews_pending(self, project_id: str) -> int:
        async with httpx.AsyncClient(headers=self._headers) as c:
            r = raise_for_status(
                await c.get(f"{self._base_url}/api/v1/projects/{project_id}/reviews/pending")
            )
            return int(r.json().get("count", 0))
