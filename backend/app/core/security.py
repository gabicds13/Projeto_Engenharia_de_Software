"""Autenticação JWT do BFF.

Aceita:
- tokens de desenvolvimento do próprio Módulo 6;
- tokens RS256 reais emitidos pelo Módulo 1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

import httpx
from fastapi import Depends, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import Settings, get_settings
from app.core.errors import ForbiddenError, UnauthorizedError


class Role(str, Enum):
    PO = "PO"
    PM = "PM"
    DEV = "DEV"


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    role: Role | None
    project_ids: tuple[str, ...]
    access_token: str = field(repr=False, default="")

    def can_access_project(self, project_id: str) -> bool:
        return project_id in self.project_ids


_bearer = HTTPBearer(auto_error=False)


def _decode_dev_token(token: str, settings: Settings) -> dict:
    """Valida os tokens antigos usados somente para desenvolvimento."""
    options = {}

    if settings.jwt_audience is None:
        options["verify_aud"] = False

    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options=options,
    )


async def _decode_module1_token(token: str, settings: Settings) -> dict:
    """Valida um JWT RS256 real emitido pelo Módulo 1."""

    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise UnauthorizedError("Token inválido.") from exc

    kid = header.get("kid")

    if not kid:
        raise UnauthorizedError("Token sem identificador de chave (kid).")

    try:
        async with httpx.AsyncClient(
            timeout=settings.upstream_timeout_seconds
        ) as client:
            response = await client.get(settings.module1_jwks_url)
            response.raise_for_status()
            jwks = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise UnauthorizedError(
            "Não foi possível validar o token com o Módulo 1."
        ) from exc

    public_key = next(
        (key for key in jwks.get("keys", []) if key.get("kid") == kid),
        None,
    )

    if public_key is None:
        raise UnauthorizedError("Chave pública do token não encontrada.")

    try:
        return jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.module1_jwt_audience,
            issuer=settings.module1_jwt_issuer,
        )
    except JWTError as exc:
        raise UnauthorizedError("Token inválido ou expirado.") from exc


async def _decode(token: str, settings: Settings) -> dict:
    """Escolhe o validador conforme o algoritmo do token."""

    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise UnauthorizedError("Token inválido.") from exc

    algorithm = header.get("alg")

    # Token real do Módulo 1
    if algorithm == "RS256":
        return await _decode_module1_token(token, settings)

    # Mantemos temporariamente o login de desenvolvimento.
    if algorithm == settings.jwt_algorithm and settings.dev_login_enabled:
        try:
            return _decode_dev_token(token, settings)
        except JWTError as exc:
            raise UnauthorizedError("Token inválido ou expirado.") from exc

    raise UnauthorizedError("Algoritmo de autenticação não permitido.")


def _user_from_claims(
    claims: dict,
    access_token: str = "",
) -> CurrentUser:
    """Transforma as claims do JWT em usuário do BFF."""

    user_id = claims.get("sub") or claims.get("user_id")

    if not user_id:
        raise UnauthorizedError("Token sem identificação do usuário.")

    role_raw = claims.get("role")
    role: Role | None = None

    if role_raw:
        try:
            role = Role(role_raw)
        except ValueError as exc:
            raise UnauthorizedError("Papel inválido no token.") from exc

    project_ids = claims.get("project_ids", [])

    if not isinstance(project_ids, list):
        project_ids = []

    return CurrentUser(
        user_id=str(user_id),
        role=role,
        project_ids=tuple(str(project_id) for project_id in project_ids),
        access_token=access_token,
    )


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if creds is None or not creds.credentials:
        raise UnauthorizedError("Credenciais ausentes.")

    claims = await _decode(creds.credentials, settings)

    return _user_from_claims(
        claims,
        access_token=creds.credentials,
    )
    

def require_role(*roles: Role):
    """Dependência usada pelas rotas antigas baseadas nos perfis do MVP."""

    async def _dep(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if user.role is None or user.role not in roles:
            raise ForbiddenError("Papel sem permissão para esta ação.")

        return user

    return _dep


async def ws_authenticate(websocket: WebSocket) -> CurrentUser:
    """Autentica WebSocket pelo token informado em ?token=."""

    settings = get_settings()
    token = websocket.query_params.get("token")

    if not token:
        raise UnauthorizedError("Token ausente no handshake.")

    claims = await _decode(token, settings)

    return _user_from_claims(claims)


def downstream_headers(user: CurrentUser) -> dict[str, str]:
    """Compatibilidade temporária com os serviços atuais do MVP."""

    headers = {
        "X-User-Id": user.user_id,
        "X-Project-Ids": ",".join(user.project_ids),
    }

    if user.role is not None:
        headers["X-User-Role"] = user.role.value

    return headers


def issue_dev_token(role: Role, settings: Settings) -> str:
    """Continua gerando tokens locais enquanto fazemos a integração."""

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

    return jwt.encode(
        claims,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )