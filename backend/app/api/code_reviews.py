"""API BFF do Módulo 4: histórico de PRs acessíveis, sem credenciais no frontend."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.clients.code_review_client import (
    CodeReviewUnavailable,
    HttpCodeReviewClient,
    project_repository_names,
)
from app.clients.code_review_metrics_client import fetch_code_review_metrics
from app.clients.projects_client import ensure_project_access
from app.core.config import Settings, get_settings
from app.core.errors import ForbiddenError, ServiceUnavailableError
from app.core.security import CurrentUser, get_current_user

router = APIRouter(prefix="/api/bff/code-reviews", tags=["code-reviews"])


@router.get("")
async def list_code_reviews(
    project_id: str = Query(..., min_length=1, max_length=128),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Últimas revisões de PR vinculados aos repositórios autorizados no M2.

    Atenção: o histórico global do M4 é limitado a 20 entradas.
    Não representa todo o histórico nem a contagem de revisões pendentes.
    """
    # Primeiro valida acesso no M1. Sem acesso não consulta M2 ou M4.
    if user.role is not None:
        if not user.can_access_project(project_id):
            raise ForbiddenError("Usuário não participa deste projeto.")
    else:
        await ensure_project_access(project_id, user, settings)

    if not settings.code_review_enabled:
        raise ServiceUnavailableError("Integração com o Módulo 4 não está ativada.")
    if not settings.code_review_password:
        raise ServiceUnavailableError("Integração com o Módulo 4 não está configurada.")
    if not settings.github_url.startswith("https://") or not settings.code_review_url.startswith("https://"):
        raise ServiceUnavailableError("Integração com o Módulo 4 exige HTTPS.")

    try:
        allowed = await project_repository_names(
            github_url=settings.github_url,
            project_id=project_id,
            access_token=user.access_token,
            timeout=settings.code_review_timeout_seconds,
        )
        client = HttpCodeReviewClient(
            base_url=settings.code_review_url,
            username=settings.code_review_username,
            password=settings.code_review_password,
            timeout=settings.code_review_timeout_seconds,
        )
        items = await client.history(allowed)
    except CodeReviewUnavailable as exc:
        raise ServiceUnavailableError("Histórico do Módulo 4 indisponível no momento.") from exc

    return {
        "project_id": project_id,
        "source": "module-4",
        "history_limited": True,
        "pending_reviews": None,
        "items": items,
    }


@router.get("/metrics")
async def code_review_metrics(
    project_id: UUID = Query(...),
    dias: int = Query(14, ge=1, le=90),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Consulta contagens do projeto M1 autorizado, sem credenciais no M4."""
    project = str(project_id)
    await ensure_project_access(project, user, settings)
    if not settings.code_review_enabled:
        raise ServiceUnavailableError("Integração com o Módulo 4 não está ativada.")
    try:
        metrics = await fetch_code_review_metrics(
            base_url=settings.code_review_url,
            project_id=project,
            days=dias,
            timeout=settings.code_review_timeout_seconds,
        )
    except CodeReviewUnavailable as exc:
        raise ServiceUnavailableError("Métricas do Módulo 4 indisponíveis no momento.") from exc
    return {
        "project_id": project,
        "dias": dias,
        "source": "module-4",
        "data_origin": "real",
        "metrics": metrics,
    }
