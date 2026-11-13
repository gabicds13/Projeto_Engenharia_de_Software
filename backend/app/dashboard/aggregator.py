"""Agrega as métricas do dashboard a partir dos Módulos 1 e 2.

Cada card é montado de forma independente através do `guarded_call`: a falha de um
serviço de origem deixa apenas aquele card como `unavailable`, sem afetar os demais
(degradação graciosa — Requisito 4.3/4.4).
"""
from __future__ import annotations

import asyncio

from app.clients.backlog_client import BacklogClient
from app.clients.github_client import GithubClient
from app.core.resilience import ResilienceRegistry, UpstreamUnavailable
from app.domain.schemas import DashboardCard, DashboardResponse


class MetricsAggregator:
    def __init__(
        self,
        backlog: BacklogClient,
        github: GithubClient,
        registry: ResilienceRegistry,
        mock_keys: frozenset[str] = frozenset(),
    ):
        self._backlog = backlog
        self._github = github
        self._reg = registry
        self._mock_keys = mock_keys

    async def _card(self, key: str, project_id: str, factory) -> DashboardCard:
        origin = "mock" if key in self._mock_keys else "real"
        try:
            result = await self._reg.guarded_call(f"{key}:{project_id}", factory)
        except UpstreamUnavailable:
            return DashboardCard(key=key, state="unavailable", stale=False, data_origin=origin, value=None)
        value = result.value
        # Serializa pydantic -> dict quando aplicável
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="json")
        return DashboardCard(key=key, state="ok", stale=result.stale, data_origin=origin, value=value)

    async def build(self, project_id: str) -> DashboardResponse:
        # As fontes sao independentes: consultar em paralelo evita somar atrasos.
        commits, open_prs, reviews, stories, weekly = await asyncio.gather(
            self._card(
                "commits_week",
                project_id,
                lambda: self._github.commits_this_week(project_id),
            ),
            self._card(
                "open_prs",
                project_id,
                lambda: self._github.open_prs(project_id),
            ),
            self._card(
                "reviews_pending",
                project_id,
                lambda: self._backlog.reviews_pending(project_id),
            ),
            self._card(
                "stories_by_status",
                project_id,
                lambda: self._backlog.stories_by_status(project_id),
            ),
            self._card(
                "weekly",
                project_id,
                lambda: self._github.weekly_commits_prs(project_id),
            ),
        )
        return DashboardResponse(
            project_id=project_id,
            cards=[commits, open_prs, reviews, stories],
            weekly=weekly,
        )
