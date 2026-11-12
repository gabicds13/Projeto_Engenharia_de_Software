"""Consulta papéis por projeto no Módulo 1, usando o JWT já autenticado.

O resultado só personaliza a visualização das notificações; não concede permissões.
Falhas de integração retornam None para preservar a relevância geral.
"""
from __future__ import annotations

import time
import unicodedata
from datetime import datetime, UTC
from typing import Any

import httpx

from app.core.config import Settings
from app.core.security import CurrentUser, Role

_CACHE_TTL_SECONDS = 60.0
_cached_roles: dict[tuple[str, str], tuple[float, tuple[Role, ...]]] = {}

_ROLE_ALIASES: dict[str, Role] = {
    "po": Role.PO,
    "product owner": Role.PO,
    "productowner": Role.PO,
    "pm": Role.PM,
    "pm scrum master": Role.PM,
    "project manager": Role.PM,
    "scrum master": Role.PM,
    "dev": Role.DEV,
    "developer": Role.DEV,
    "desenvolvedor": Role.DEV,
}


def _parse_role(raw: Any) -> Role | None:
    if not isinstance(raw, str):
        return None
    unaccented = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode()
    normalized = " ".join(
        unaccented.lower().replace("-", " ").replace("_", " ").replace("/", " ").split()
    )
    return _ROLE_ALIASES.get(normalized)


def _active(member: dict) -> bool:
    expiration = member.get("expires_at")
    if not expiration:
        return True
    if not isinstance(expiration, str):
        return False
    try:
        date = datetime.fromisoformat(expiration.replace("Z", "+00:00"))
        return date.tzinfo is not None and date > datetime.now(UTC)
    except ValueError:
        return False


async def get_project_roles(
    project_id: str,
    user: CurrentUser,
    settings: Settings,
) -> tuple[Role, ...] | None:
    """Retorna papéis por projeto, ou None se não foi possível confirmar.

    A propriedade is_owner NÃO é convertida em PO: dono do projeto e
    Product Owner são coisas diferentes.
    """
    if not user.access_token or settings.use_mocks:
        return None

    key = (user.user_id, project_id)
    cached = _cached_roles.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    try:
        async with httpx.AsyncClient(
            timeout=settings.upstream_timeout_seconds,
        ) as client:
            for offset in range(0, 1000, 100):
                response = await client.get(
                    f"{settings.module1_projects_url.rstrip('/')}/projects/{project_id}/members",
                    params={"limit": 100, "offset": offset},
                    headers={"Authorization": f"Bearer {user.access_token}"},
                )
                if response.status_code != 200:
                    return None

                payload = response.json()
                if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
                    return None

                items = payload["items"]
                for member in items:
                    if isinstance(member, dict) and str(member.get("user_id")) == user.user_id:
                        raw_roles = member.get("roles", [])
                        if not isinstance(raw_roles, list) or not _active(member):
                            result: tuple[Role, ...] = ()
                        else:
                            result = tuple(dict.fromkeys(
                                role for value in raw_roles
                                if (role := _parse_role(value)) is not None
                            ))
                        if len(_cached_roles) >= 1024:
                            _cached_roles.clear()
                        _cached_roles[key] = (time.monotonic() + _CACHE_TTL_SECONDS, result)
                        return result

                total = payload.get("total")
                if len(items) < 100 or (isinstance(total, int) and offset + len(items) >= total):
                    break

    except (httpx.HTTPError, ValueError, TypeError):
        return None

    # Uma lista completa sem o integrante não confirma nenhum papel.
    result = ()
    if len(_cached_roles) >= 1024:
        _cached_roles.clear()
    _cached_roles[key] = (time.monotonic() + _CACHE_TTL_SECONDS, result)
    return result
