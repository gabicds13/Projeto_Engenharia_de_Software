"""Contrato M2 real e isolamento do dashboard, usando apenas respostas fictícias."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.clients.base import UpstreamError
from app.clients.github_client import HttpGithubClient, MockGithubClient
from app.clients.backlog_client import MockBacklogClient
from app.core.resilience import ResilienceRegistry
from app.dashboard.aggregator import MetricsAggregator


def _registry():
    return ResilienceRegistry(
        timeout_seconds=1, fails_to_open=3, reset_seconds=10, cache_ttl_seconds=30
    )


def _m2_mock(monkeypatch, *, today=None):
    today = today or datetime.now(UTC)
    calls = []
    monday = (today - timedelta(days=today.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    async def fake_get(self, path, params):
        calls.append((path, dict(params), dict(self._headers)))
        if path == "/api/v1/repositories":
            return [
                {"id": 11, "project_id": "proj-123"},
                {"id": 12, "project_id": "proj-123"},
            ]
        rid = params["repository_id"]
        if path == "/api/v1/metrics/dashboard":
            return {
                "repository": {"id": rid},
                "period_days": 7,
                "total_commits": 3 if rid == 11 else 5,
                "prs_open": 1 if rid == 11 else 2,
            }
        if path == "/api/v1/commits":
            return {
                "results": [
                    {"authored_at": (monday - timedelta(weeks=1)).isoformat()},
                    {"authored_at": (monday + timedelta(days=1)).isoformat()},
                ] if rid == 11 else [],
                "next": None,
            }
        if path == "/api/v1/pull-requests":
            return {
                "results": [
                    {"opened_at": (monday + timedelta(days=2)).isoformat()},
                ] if rid == 12 else [],
                "next": None,
            }
        raise AssertionError(f"Rota inesperada: {path}")

    monkeypatch.setattr(HttpGithubClient, "_get", fake_get)
    return calls


@pytest.mark.asyncio
async def test_m2_real_soma_kpis_dos_repositorios_do_projeto(monkeypatch):
    calls = _m2_mock(monkeypatch)
    github = HttpGithubClient("https://m2.example", headers={"Authorization": "Bearer token-autorizado"})
    assert await github.commits_this_week("proj-123") == 8
    assert await github.open_prs("proj-123") == 3
    assert calls
    assert all(h.get("Authorization") == "Bearer token-autorizado" for _, _, h in calls)
    assert all(p.get("project_id") == "proj-123" for path, p, _ in calls if path.endswith("repositories"))


@pytest.mark.asyncio
async def test_m2_real_monta_grafico_sem_dados_inventados(monkeypatch):
    _m2_mock(monkeypatch)
    github = HttpGithubClient("https://m2.example")
    series = await github.weekly_commits_prs("proj-123")
    assert len(series.points) == 5
    assert series.points[-2].commits == 1
    assert series.points[-1].commits == 1
    assert series.points[-1].prs == 1


@pytest.mark.asyncio
async def test_m2_nao_mostra_zero_se_usuario_nao_tem_repositorio(monkeypatch):
    async def empty(self, path, params):
        return []
    monkeypatch.setattr(HttpGithubClient, "_get", empty)
    with pytest.raises(UpstreamError, match="Nenhum repositório"):
        await HttpGithubClient("https://m2.example").open_prs("proj-123")


@pytest.mark.asyncio
async def test_m2_rejeita_repositorio_de_outro_projeto(monkeypatch):
    async def wrong_project(self, path, params):
        return [{"id": 33, "project_id": "proj-diferente"}]
    monkeypatch.setattr(HttpGithubClient, "_get", wrong_project)
    with pytest.raises(UpstreamError, match="fora do projeto"):
        await HttpGithubClient("https://m2.example").commits_this_week("proj-123")


@pytest.mark.asyncio
async def test_m2_nao_aceita_paginacao_truncada(monkeypatch):
    async def never_ends(self, path, params):
        return {"results": [], "next": "?page=2"}
    monkeypatch.setattr(HttpGithubClient, "_get", never_ends)
    with pytest.raises(UpstreamError, match="Paginação acima"):
        await HttpGithubClient("https://m2.example")._all_pages(
            "/api/v1/commits", 1
        )


@pytest.mark.asyncio
async def test_cache_dashboard_isolado_por_usuario():
    class G(MockGithubClient):
        def __init__(self, count):
            self.count = count

        async def commits_this_week(self, project_id):
            return self.count

    registry = _registry()
    a = await MetricsAggregator(
        MockBacklogClient(), G(10), registry, cache_scope="user:alice"
    ).build("proj-123")
    b = await MetricsAggregator(
        MockBacklogClient(), G(20), registry, cache_scope="user:bob"
    ).build("proj-123")
    a_card = next(card for card in a.cards if card.key == "commits_week")
    b_card = next(card for card in b.cards if card.key == "commits_week")
    assert a_card.value == 10 and b_card.value == 20
    assert not a_card.stale and not b_card.stale
