"""Client do Módulo 2 (GitHub): commits/PRs por semana e PRs abertos."""
from __future__ import annotations

from typing import Protocol

import httpx

from app.clients.base import UpstreamError, raise_for_status
from app.domain.schemas import WeeklyPoint, WeeklySeries


class GithubClient(Protocol):
    async def weekly_commits_prs(self, project_id: str) -> WeeklySeries: ...
    async def open_prs(self, project_id: str) -> int: ...
    async def commits_this_week(self, project_id: str) -> int: ...


class MockGithubClient:
    async def weekly_commits_prs(self, project_id: str) -> WeeklySeries:
        return WeeklySeries(
            points=[
                WeeklyPoint(week="2026-W37", commits=42, prs=6),
                WeeklyPoint(week="2026-W38", commits=51, prs=8),
                WeeklyPoint(week="2026-W39", commits=38, prs=5),
                WeeklyPoint(week="2026-W40", commits=63, prs=9),
                WeeklyPoint(week="2026-W41", commits=47, prs=7),
            ]
        )

    async def open_prs(self, project_id: str) -> int:
        return 7

    async def commits_this_week(self, project_id: str) -> int:
        return 47


class HttpGithubClient:
    def __init__(self, base_url: str, headers: dict[str, str] | None = None):
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}

    async def weekly_commits_prs(self, project_id: str) -> WeeklySeries:
        async with httpx.AsyncClient(headers=self._headers) as c:
            r = raise_for_status(
                await c.get(f"{self._base_url}/api/v1/projects/{project_id}/metrics/weekly")
            )
            try:
                return WeeklySeries.model_validate(r.json())
            except Exception as exc:  # noqa: BLE001
                raise UpstreamError(f"resposta inválida do github: {exc}") from exc

    async def open_prs(self, project_id: str) -> int:
        async with httpx.AsyncClient(headers=self._headers) as c:
            r = raise_for_status(
                await c.get(f"{self._base_url}/api/v1/projects/{project_id}/prs/open")
            )
            return int(r.json().get("count", 0))

    async def commits_this_week(self, project_id: str) -> int:
        async with httpx.AsyncClient(headers=self._headers) as c:
            r = raise_for_status(
                await c.get(f"{self._base_url}/api/v1/projects/{project_id}/commits/week")
            )
            return int(r.json().get("count", 0))
