"""Autenticação JWT e repasse de identidade aos serviços downstream.

O token é emitido pelo Módulo 1 (Auth). Aqui apenas validamos e extraímos as
claims (user_id, role, project_ids). Em desenvolvimento, oferecemos uma rota que
gera tokens de teste para os três perfis.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import Depends, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import Settings, get_settings
from app.core.errors import ForbiddenError, UnauthorizedError


class Role(str, Enum):
    PO = "PO"
    PM = "PM"  # Gerente de Projetos / Scrum Master
    DEV = "DEV"


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    role: Role
    project_ids: tuple[str, ...]

    def can_access_project(self, project_id: str) -> bool:
        return project_id in self.project_ids


_bearer = HTTPBearer(auto_error=False)


def _decode(token: str, settings: Settings) -> dict:
    options = {}
    if settings.jwt_audience is None:
        options["verify_aud"] = False
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options=options,
        )
    except JWTError as exc:
        raise UnauthorizedError("Token inválido ou expirado.") from exc


def _user_from_claims(claims: dict) -> CurrentUser:
    user_id = claims.get("sub") or claims.get("user_id")
    role_raw = claims.get("role")
    project_ids = claims.get("project_ids", [])
    if not user_id or not role_raw:
        raise UnauthorizedError("Token sem claims obrigatórias (sub/role).")
    try:
        role = Role(role_raw)
    except ValueError as exc:
        raise UnauthorizedError("Papel inválido no token.") from exc
    if not isinstance(project_ids, list):
        raise UnauthorizedError("project_ids inválido no token.")
    return CurrentUser(user_id=str(user_id), role=role, project_ids=tuple(project_ids))


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if creds is None or not creds.credentials:
        raise UnauthorizedError("Credenciais ausentes.")
    return _user_from_claims(_decode(creds.credentials, settings))


def require_role(*roles: Role):
    """Dependência que exige um dos papéis informados (senão 403)."""

    async def _dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise ForbiddenError("Papel sem permissão para esta ação.")
        return user

    return _dep


async def ws_authenticate(websocket: WebSocket) -> CurrentUser:
    """Autentica o handshake do WebSocket (token em query string ?token=...)."""
    settings = get_settings()
    token = websocket.query_params.get("token")
    if not token:
        raise UnauthorizedError("Token ausente no handshake.")
    return _user_from_claims(_decode(token, settings))


def downstream_headers(user: CurrentUser) -> dict[str, str]:
    """Headers para repassar a identidade do usuário aos serviços downstream."""
    return {
        "X-User-Id": user.user_id,
        "X-User-Role": user.role.value,
        "X-Project-Ids": ",".join(user.project_ids),
    }


def issue_dev_token(role: Role, settings: Settings) -> str:
    """Gera um JWT de teste (apenas em desenvolvimento)."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": f"dev-{role.value.lower()}",
        "role": role.value,
        "project_ids": ["proj-123", "proj-456"],
        "iat": now,
        "exp": now + timedelta(hours=8),
    }
    if settings.jwt_issuer:
        claims["iss"] = settings.jwt_issuer
    if settings.jwt_audience:
        claims["aud"] = settings.jwt_audience
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
