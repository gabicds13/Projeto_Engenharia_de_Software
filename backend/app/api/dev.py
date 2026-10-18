"""Rotas de desenvolvimento: geração de tokens de teste para os três perfis.

Montadas apenas quando APP_ENV=development.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.security import Role, issue_dev_token

router = APIRouter(prefix="/api/bff/dev", tags=["dev"])


@router.get("/tokens")
async def dev_tokens(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """Devolve um JWT de teste para PO, PM e Dev (uso local sem o Módulo 1)."""
    return {
        "po": issue_dev_token(Role.PO, settings),
        "pm": issue_dev_token(Role.PM, settings),
        "dev": issue_dev_token(Role.DEV, settings),
    }
