"""Rota do dashboard: agrega métricas dos Módulos 1 e 2."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.clients import get_backlog_client, get_github_client
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
) -> DashboardResponse:
    if not user.can_access_project(project_id):
        raise ForbiddenError("Usuário não participa deste projeto.")
    aggregator = MetricsAggregator(
        backlog=get_backlog_client(),
        github=get_github_client(),
        registry=get_registry(),
    )
    return await aggregator.build(project_id)
