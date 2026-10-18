"""Agrega as métricas do dashboard a partir dos Módulos 1 e 2.

Cada card é montado de forma independente através do `guarded_call`: a falha de um
serviço de origem deixa apenas aquele card como `unavailable`, sem afetar os demais
(degradação graciosa — Requisito 4.3/4.4).
"""
from __future__ import annotations

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
    ):
        self._backlog = backlog
        self._github = github
        self._reg = registry

    async def _card(self, key: str, project_id: str, factory) -> DashboardCard:
        try:
            result = await self._reg.guarded_call(f"{key}:{project_id}", factory)
        except UpstreamUnavailable:
            return DashboardCard(key=key, state="unavailable", stale=False, value=None)
        value = result.value
        # Serializa pydantic -> dict quando aplicável
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="json")
        return DashboardCard(key=key, state="ok", stale=result.stale, value=value)

    async def build(self, project_id: str) -> DashboardResponse:
        commits = await self._card(
            "commits_week", project_id, lambda: self._github.commits_this_week(project_id)
        )
        open_prs = await self._card(
            "open_prs", project_id, lambda: self._github.open_prs(project_id)
        )
        reviews = await self._card(
            "reviews_pending", project_id, lambda: self._backlog.reviews_pending(project_id)
        )
        stories = await self._card(
            "stories_by_status", project_id, lambda: self._backlog.stories_by_status(project_id)
        )
        weekly = await self._card(
            "weekly", project_id, lambda: self._github.weekly_commits_prs(project_id)
        )
        return DashboardResponse(
            project_id=project_id,
            cards=[commits, open_prs, reviews, stories],
            weekly=weekly,
        )
