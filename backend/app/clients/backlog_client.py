"""Client do Backlog do Módulo 1."""
from __future__ import annotations

from typing import Protocol

import httpx

from app.clients.base import UpstreamError, raise_for_status
from app.domain.schemas import StoriesByStatus


class BacklogClient(Protocol):
    async def stories_by_status(self, project_id: str) -> StoriesByStatus: ...
    async def reviews_pending(self, project_id: str) -> int: ...


class MockBacklogClient:
    """Dados de demonstração usados enquanto o Backlog real não está ativo."""

    async def stories_by_status(self, project_id: str) -> StoriesByStatus:
        return StoriesByStatus(
            todo=8,
            in_progress=5,
            in_review=3,
            done=14,
        )

    async def reviews_pending(self, project_id: str) -> int:
        return 3


class HttpBacklogClient:
    """Consome o Backlog real do Módulo 1."""

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}

    async def stories_by_status(
        self,
        project_id: str,
    ) -> StoriesByStatus:
        async with httpx.AsyncClient(
            headers=self._headers,
        ) as client:
            response = raise_for_status(
                await client.get(
                    f"{self._base_url}/projects/{project_id}/stories"
                )
            )

        try:
            data = response.json()

            if isinstance(data, list):
                stories = data
            elif isinstance(data, dict):
                stories = data.get("items", [])
            else:
                stories = []

            counts = {
                "todo": 0,
                "in_progress": 0,
                "done": 0,
            }

            for story in stories:
                status = story.get("status")

                if status in counts:
                    counts[status] += 1

            return StoriesByStatus(
                todo=counts["todo"],
                in_progress=counts["in_progress"],
                in_review=0,
                done=counts["done"],
            )

        except Exception as exc:
            raise UpstreamError(
                f"Resposta inválida do Backlog do Módulo 1: {exc}"
            ) from exc

    async def reviews_pending(
        self,
        project_id: str,
    ) -> int:
        # Reviews não pertencem ao Backlog do Módulo 1.
        # Essa métrica será integrada com o módulo responsável depois.
        raise UpstreamError(
            "Reviews pendentes não são fornecidos pelo Backlog do Módulo 1."
        )