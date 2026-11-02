"""Integração de autenticação do Módulo 6 com o Módulo 1."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.errors import UnauthorizedError


router = APIRouter(prefix="/api/bff/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(
    payload: LoginRequest,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Encaminha o login para o serviço de autenticação do Módulo 1."""

    try:
        async with httpx.AsyncClient(
            timeout=settings.upstream_timeout_seconds
        ) as client:
            response = await client.post(
                f"{settings.module1_auth_url}/auth/token",
                data={
                    "username": payload.email,
                    "password": payload.password,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
    except httpx.HTTPError as exc:
        raise UnauthorizedError(
            "Não foi possível conectar ao serviço de autenticação do Módulo 1."
        ) from exc

    if response.status_code != 200:
        raise UnauthorizedError("E-mail ou senha inválidos.")

    data = response.json()

    return {
        "access_token": data["access_token"],
        "token_type": data.get("token_type", "bearer"),
    }