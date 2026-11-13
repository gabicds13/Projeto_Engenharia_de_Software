"""Regressões finais de robustez do Módulo 6, sem serviços externos reais.

Os clientes simulam falhas locais: não alteram Azure, Neon nem outros módulos.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.clients.backlog_client import MockBacklogClient
from app.clients.github_client import MockGithubClient
from app.core.config import get_settings
from app.core.resilience import ResilienceRegistry, UpstreamUnavailable


def _registry(*, fails_to_open: int = 3, reset_seconds: float = 10.0):
    return ResilienceRegistry(
        timeout_seconds=0.5,
        fails_to_open=fails_to_open,
        reset_seconds=reset_seconds,
        cache_ttl_seconds=30.0,
    )


def _auth_headers():
    settings = get_settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "robustez-user",
            "role": "DEV",
            "project_ids": ["proj-123"],
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def test_endpoint_dashboard_retorna_200_com_modulos_1_e_2_offline(
    client, monkeypatch
):
    """Uma falha simultânea degrada os widgets, não a resposta HTTP."""

    import app.dashboard.router as dashboard_router

    class BacklogOffline(MockBacklogClient):
        async def stories_by_status(self, project_id: str):
            raise ConnectionError("Módulo 1 indisponível")

        async def reviews_pending(self, project_id: str):
            raise ConnectionError("Módulo 1 indisponível")

    class GithubOffline(MockGithubClient):
        async def commits_this_week(self, project_id: str):
            raise ConnectionError("Módulo 2 indisponível")

        async def open_prs(self, project_id: str):
            raise ConnectionError("Módulo 2 indisponível")

        async def weekly_commits_prs(self, project_id: str):
            raise ConnectionError("Módulo 2 indisponível")

    monkeypatch.setattr(
        dashboard_router, "get_backlog_client", lambda: BacklogOffline()
    )
    monkeypatch.setattr(
        dashboard_router, "get_github_client", lambda: GithubOffline()
    )
    monkeypatch.setattr(dashboard_router, "get_registry", _registry)

    response = client.get(
        "/api/bff/dashboard",
        params={"project_id": "proj-123"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["project_id"] == "proj-123"
    assert len(body["cards"]) == 4
    assert all(card["state"] == "unavailable" for card in body["cards"])
    assert all(card["value"] is None for card in body["cards"])
    assert body["weekly"]["state"] == "unavailable"


@pytest.mark.asyncio
async def test_circuit_breaker_permited_nova_tentativa_apos_recuperacao():
    """A falha inicial não bloqueia o serviço quando o breaker pode reabrir."""
    registry = _registry(fails_to_open=1, reset_seconds=0.0)
    attempts = {"count": 0}

    async def recovering_service():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise ConnectionError("falha temporária")
        return "funcionando"

    with pytest.raises(UpstreamUnavailable):
        await registry.guarded_call("modulo-externo", recovering_service)

    result = await registry.guarded_call("modulo-externo", recovering_service)
    assert result.value == "funcionando"
    assert result.stale is False
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_cache_stale_e_substituido_quando_upstream_volta():
    """Cache de falha nunca deve impedir uma resposta nova após recuperação."""
    registry = _registry()
    attempts = {"count": 0}

    async def intermittent_service():
        attempts["count"] += 1
        if attempts["count"] == 2:
            raise ConnectionError("queda momentânea")
        return {"versao": attempts["count"]}

    first = await registry.guarded_call("card", intermittent_service)
    assert first.value == {"versao": 1}
    assert first.stale is False

    during_failure = await registry.guarded_call("card", intermittent_service)
    assert during_failure.value == {"versao": 1}
    assert during_failure.stale is True

    recovered = await registry.guarded_call("card", intermittent_service)
    assert recovered.value == {"versao": 3}
    assert recovered.stale is False
