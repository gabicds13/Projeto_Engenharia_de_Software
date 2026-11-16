"""BFF protegido para o feed global de tendências (Módulo 5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.clients.curadoria_client import CuradoriaUnavailable, fetch_em_alta
from app.core.config import Settings, get_settings
from app.core.errors import ServiceUnavailableError
from app.core.security import CurrentUser, get_current_user

router = APIRouter(prefix="/api/bff/curadoria", tags=["curadoria"])


@router.get("/em-alta")
async def em_alta(
    _user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Tendências gerais, não dados/recomendações específicas de um projeto."""
    if not settings.curadoria_enabled:
        raise ServiceUnavailableError("Curadoria não ativada neste ambiente.")

    try:
        return await fetch_em_alta(
            base_url=settings.curadoria_url,
            timeout=settings.curadoria_timeout_seconds,
            limit=6,
        )
    except CuradoriaUnavailable as exc:
        raise ServiceUnavailableError("Feed do Módulo 5 indisponível no momento.") from exc
