"""Client para validar acesso a projetos no Módulo 1."""
from __future__ import annotations

import httpx

from app.core.config import Settings
from app.core.errors import (
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from app.core.security import CurrentUser


async def ensure_project_access(
    project_id: str,
    user: CurrentUser,
    settings: Settings,
) -> None:
    """Confirma no Módulo 1 se o usuário pode acessar o projeto."""

    if not user.access_token:
        raise UnauthorizedError("Token de acesso ausente.")

    try:
        async with httpx.AsyncClient(
            timeout=settings.upstream_timeout_seconds
        ) as client:
            response = await client.get(
                f"{settings.module1_projects_url}/projects/{project_id}/access/v2",
                headers={
                    "Authorization": f"Bearer {user.access_token}",
                },
            )
    except httpx.HTTPError as exc:
        raise ServiceUnavailableError(
            "Não foi possível validar o acesso ao projeto no Módulo 1."
        ) from exc

    if response.status_code == 200:
        return

    if response.status_code == 401:
        raise UnauthorizedError("Sessão inválida ou expirada.")

    if response.status_code == 403:
        raise ForbiddenError("Usuário não participa deste projeto.")

    if response.status_code == 404:
        raise NotFoundError("Projeto não encontrado.")

    raise ServiceUnavailableError(
        f"Erro ao validar acesso ao projeto ({response.status_code})."
    )
async def list_accessible_project_ids(
    user: CurrentUser,
    settings: Settings,
) -> tuple[str, ...]:
    """Retorna os IDs dos projetos que o usuário pode acessar."""

    # Tokens de desenvolvimento já carregam os projetos.
    if user.project_ids:
        return user.project_ids

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
            "Não foi possível consultar os projetos do usuário."
        ) from exc

    if response.status_code == 401:
        raise UnauthorizedError("Sessão inválida ou expirada.")

    if response.status_code == 403:
        raise ForbiddenError(
            "Usuário sem permissão para acessar projetos."
        )

    if response.status_code != 200:
        raise ServiceUnavailableError(
            f"Erro ao consultar projetos no Módulo 1 ({response.status_code})."
        )

    data = response.json()

    if isinstance(data, list):
        projects = data
    elif isinstance(data, dict):
        projects = data.get("items") or data.get("projects") or []
    else:
        projects = []

    project_ids: list[str] = []

    for project in projects:
        if not isinstance(project, dict):
            continue

        project_id = project.get("project_id") or project.get("id")

        if project_id:
            project_ids.append(str(project_id))

    return tuple(dict.fromkeys(project_ids))