"""Testes de autenticação e autorização (Requisitos 2.2, 2.4, 2.5)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.security import CurrentUser, Role, get_current_user, require_role


@pytest.fixture
def app_with_protected_routes():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/me")
    async def me(user: CurrentUser = Depends(get_current_user)):
        return {"user_id": user.user_id, "role": user.role.value}

    @app.get("/po-only")
    async def po_only(user: CurrentUser = Depends(require_role(Role.PO, Role.PM))):
        return {"ok": True}

    return app


@pytest.fixture
def auth_client(app_with_protected_routes):
    return TestClient(app_with_protected_routes)


def _token(role: str = "DEV", **overrides) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": "user-1",
        "role": role,
        "project_ids": ["proj-123"],
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    claims.update(overrides)
    return jwt.encode(claims, s.jwt_secret, algorithm=s.jwt_algorithm)


def test_valid_token_authenticates(auth_client):
    r = auth_client.get("/me", headers={"Authorization": f"Bearer {_token('DEV')}"})
    assert r.status_code == 200
    assert r.json() == {"user_id": "user-1", "role": "DEV"}


def test_missing_token_returns_401(auth_client):
    r = auth_client.get("/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_expired_token_returns_401(auth_client):
    expired = _token("DEV", exp=datetime.now(UTC) - timedelta(hours=1))
    r = auth_client.get("/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


def test_tampered_signature_returns_401(auth_client):
    bad = _token("DEV")[:-3] + "xxx"
    r = auth_client.get("/me", headers={"Authorization": f"Bearer {bad}"})
    assert r.status_code == 401


def test_wrong_role_returns_403(auth_client):
    r = auth_client.get("/po-only", headers={"Authorization": f"Bearer {_token('DEV')}"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_allowed_role_passes(auth_client):
    r = auth_client.get("/po-only", headers={"Authorization": f"Bearer {_token('PO')}"})
    assert r.status_code == 200


def test_dev_tokens_endpoint(client):
    r = client.get("/api/bff/dev/tokens")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"po", "pm", "dev"}
    # Os tokens emitidos devem ser aceitos pela própria validação.
    s = get_settings()
    claims = jwt.decode(body["po"], s.jwt_secret, algorithms=[s.jwt_algorithm])
    assert claims["role"] == "PO"


@pytest.mark.asyncio
async def test_producao_rejeita_token_de_desenvolvimento():
    from app.core.config import Settings
    from app.core.errors import UnauthorizedError
    from app.core.security import _decode

    settings = Settings(_env_file=None, app_env="production", enable_dev_login=False)
    now = datetime.now(UTC)
    development_token = jwt.encode(
        {
            "sub": "dev-po",
            "role": "PO",
            "project_ids": ["proj-123"],
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(UnauthorizedError):
        await _decode(development_token, settings)


@pytest.mark.asyncio
async def test_token_expirado_nao_pode_acessar_dados():
    from app.core.config import Settings
    from app.core.errors import UnauthorizedError
    from app.core.security import _decode

    settings = Settings(_env_file=None, app_env="development")
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "user-test",
            "project_ids": ["proj-123"],
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(UnauthorizedError):
        await _decode(token, settings)


def test_producao_nao_monta_endpoint_de_login_dev(monkeypatch):
    import app.main as main_module
    from app.core.config import Settings

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(_env_file=None, app_env="production", enable_dev_login=False),
    )
    application = main_module.create_app()
    # O OpenAPI contém somente as rotas HTTP publicadas pela aplicação.
    paths = set(application.openapi()["paths"])
    assert "/api/bff/dev/tokens" not in paths
