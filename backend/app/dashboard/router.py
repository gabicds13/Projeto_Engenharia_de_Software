"""Rota do dashboard: agrega métricas dos Módulos 1 e 2."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.clients import get_backlog_client, get_github_client
from app.clients.backlog_client import HttpBacklogClient, MockBacklogClient
from app.clients.github_client import HttpGithubClient, MockGithubClient
from app.clients.projects_client import ensure_project_access
from app.core.config import Settings, get_settings
from app.core.errors import ForbiddenError
from app.core.resilience import get_registry
from app.core.security import CurrentUser, get_current_user
from app.dashboard.aggregator import MetricsAggregator
from app.domain.schemas import DashboardResponse

router = APIRouter(prefix="/api/bff/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    project_id: str = Query(..., description="Projeto cujas métricas serão agregadas"),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DashboardResponse:

    if user.role is not None:
        if not user.can_access_project(project_id):
            raise ForbiddenError("Usuário não participa deste projeto.")
    else:
        await ensure_project_access(project_id, user, settings)

    if user.role is not None or settings.use_backlog_mock:
        backlog_client = get_backlog_client()
    else:
        backlog_client = HttpBacklogClient(
            settings.module1_backlog_url,
            headers={
                "Authorization": f"Bearer {user.access_token}",
            },
        )

    # O Módulo 2 exige Bearer RS256 do Módulo 1 e isola métricas por usuário.
    # A flag permite testar M2 real mantendo mocks nos outros módulos.
    if settings.use_githubsync_real or not settings.use_mocks:
        github_client = HttpGithubClient(
            settings.github_url,
            headers={"Authorization": f"Bearer {user.access_token}"},
        )
    else:
        github_client = get_github_client()
    mock_keys: set[str] = set()
    if isinstance(github_client, MockGithubClient):
        mock_keys.update(("commits_week", "open_prs", "weekly"))
    if isinstance(backlog_client, MockBacklogClient):
        mock_keys.update(("reviews_pending", "stories_by_status"))

    aggregator = MetricsAggregator(
        backlog=backlog_client,
        github=github_client,
        registry=get_registry(),
        mock_keys=frozenset(mock_keys),
        cache_scope=f"user:{user.user_id}",
    )

    return await aggregator.build(project_id)