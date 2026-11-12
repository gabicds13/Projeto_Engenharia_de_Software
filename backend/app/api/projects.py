"""Integração do Módulo 6 com a API de Projetos do Módulo 1."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.errors import (
    ForbiddenError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from app.core.security import CurrentUser, get_current_user

router = APIRouter(prefix="/api/bff/projects", tags=["projects"])


@router.get("")
async def list_projects(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Lista os projetos aos quais o usuário tem acesso no Módulo 1."""

    if not user.access_token:
        raise UnauthorizedError("Token de acesso ausente.")

    try:
        async with httpx.AsyncClient(
            timeout=settings.upstream_timeout_seconds
        ) as client:
            response = await client.get(
                f"{settings.module1_projects_url}/projects",
                headers={
                    "Authorization": f"Bearer {user.access_token}",
                },
            )
    except httpx.HTTPError as exc:
        raise ServiceUnavailableError(
            "Não foi possível conectar ao serviço de projetos do Módulo 1."
        ) from exc

    if response.status_code == 401:
        raise UnauthorizedError("Sessão inválida ou expirada.")

    if response.status_code == 403:
        raise ForbiddenError("Usuário sem permissão para acessar os projetos.")

    if response.status_code >= 500:
        raise ServiceUnavailableError(
            "O serviço de projetos do Módulo 1 está indisponível."
        )

    if response.status_code != 200:
        raise ServiceUnavailableError(
            f"Erro ao consultar projetos no Módulo 1 ({response.status_code})."
        )

    return response.json()