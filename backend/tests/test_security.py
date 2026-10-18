"""Testes de autenticação e autorização (Requisitos 2.2, 2.4, 2.5)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
    now = datetime.now(timezone.utc)
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
    expired = _token("DEV", exp=datetime.now(timezone.utc) - timedelta(hours=1))
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
