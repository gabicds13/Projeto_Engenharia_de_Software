"""Testes do agregador do dashboard (Requisitos 4.1, 4.3, 4.4)."""
from __future__ import annotations

from app.clients.backlog_client import MockBacklogClient
from app.clients.github_client import MockGithubClient
from app.core.resilience import ResilienceRegistry
from app.dashboard.aggregator import MetricsAggregator


def _registry() -> ResilienceRegistry:
    return ResilienceRegistry(
        timeout_seconds=1.0, fails_to_open=3, reset_seconds=10.0, cache_ttl_seconds=30.0
    )


class _BrokenGithub(MockGithubClient):
    async def commits_this_week(self, project_id: str) -> int:
        raise RuntimeError("github fora do ar")


async def test_build_all_cards_ok():
    agg = MetricsAggregator(MockBacklogClient(), MockGithubClient(), _registry())
    resp = await agg.build("proj-123")
    keys = {c.key for c in resp.cards}
    assert keys == {"commits_week", "open_prs", "reviews_pending", "stories_by_status"}
    assert all(c.state == "ok" for c in resp.cards)
    assert resp.weekly.state == "ok"
    commits = next(c for c in resp.cards if c.key == "commits_week")
    assert commits.value == 47


async def test_one_failing_card_is_unavailable_others_ok():
    agg = MetricsAggregator(MockBacklogClient(), _BrokenGithub(), _registry())
    resp = await agg.build("proj-123")
    by_key = {c.key: c for c in resp.cards}
    # Só o card do commits (github) deve ficar indisponível
    assert by_key["commits_week"].state == "unavailable"
    assert by_key["reviews_pending"].state == "ok"
    assert by_key["stories_by_status"].state == "ok"


async def test_cache_serves_stale_after_failure():
    reg = _registry()

    class Flaky(MockGithubClient):
        def __init__(self):
            self.calls = 0

        async def commits_this_week(self, project_id: str) -> int:
            self.calls += 1
            if self.calls == 1:
                return 47
            raise RuntimeError("down")

    gh = Flaky()
    agg = MetricsAggregator(MockBacklogClient(), gh, reg)

    first = await agg.build("proj-123")
    assert next(c for c in first.cards if c.key == "commits_week").value == 47

    second = await agg.build("proj-123")
    commits = next(c for c in second.cards if c.key == "commits_week")
    assert commits.state == "ok"
    assert commits.stale is True
    assert commits.value == 47



class _FullyBrokenGithub(MockGithubClient):
    """Simula indisponibilidade completa do Módulo 2."""
    async def commits_this_week(self, project_id: str) -> int:
        raise ConnectionError("modulo 2 indisponivel")

    async def open_prs(self, project_id: str) -> int:
        raise ConnectionError("modulo 2 indisponivel")

    async def weekly_commits_prs(self, project_id: str):
        raise ConnectionError("modulo 2 indisponivel")


class _BrokenBacklog(MockBacklogClient):
    """Simula indisponibilidade completa do Backlog do Módulo 1."""
    async def stories_by_status(self, project_id: str):
        raise ConnectionError("modulo 1 indisponivel")

    async def reviews_pending(self, project_id: str) -> int:
        raise ConnectionError("modulo 1 indisponivel")


async def test_queda_total_modulo2_nao_afeta_metricas_modulo1():
    resp = await MetricsAggregator(
        MockBacklogClient(), _FullyBrokenGithub(), _registry()
    ).build("proj-123")
    cards = {c.key: c for c in resp.cards}
    assert cards["commits_week"].state == "unavailable"
    assert cards["open_prs"].state == "unavailable"
    assert resp.weekly.state == "unavailable"
    assert cards["stories_by_status"].state == "ok"
    assert cards["reviews_pending"].state == "ok"


async def test_queda_total_backlog_modulo1_nao_afeta_github():
    resp = await MetricsAggregator(
        _BrokenBacklog(), MockGithubClient(), _registry()
    ).build("proj-123")
    cards = {c.key: c for c in resp.cards}
    assert cards["stories_by_status"].state == "unavailable"
    assert cards["reviews_pending"].state == "unavailable"
    assert cards["commits_week"].state == "ok"
    assert cards["open_prs"].state == "ok"
    assert resp.weekly.state == "ok"


async def test_queda_ambos_modulos_dashboard_responde_sem_erro():
    resp = await MetricsAggregator(
        _BrokenBacklog(), _FullyBrokenGithub(), _registry()
    ).build("proj-123")
    assert resp.project_id == "proj-123"
    assert len(resp.cards) == 4
    assert all(c.state == "unavailable" for c in resp.cards)
    assert resp.weekly.state == "unavailable"


async def test_origem_simulada_identifica_apenas_metricas_mockadas():
    agg = MetricsAggregator(
        MockBacklogClient(),
        MockGithubClient(),
        _registry(),
        mock_keys=frozenset({"commits_week", "open_prs", "weekly"}),
    )
    response = await agg.build("proj-123")
    cards = {card.key: card for card in response.cards}
    assert cards["commits_week"].data_origin == "mock"
    assert cards["open_prs"].data_origin == "mock"
    assert response.weekly.data_origin == "mock"
    assert cards["stories_by_status"].data_origin == "real"
    assert cards["reviews_pending"].data_origin == "real"


async def test_metrica_simulada_indisponivel_nao_recebe_valor_falso():
    agg = MetricsAggregator(
        MockBacklogClient(),
        _FullyBrokenGithub(),
        _registry(),
        mock_keys=frozenset({"commits_week", "open_prs", "weekly"}),
    )
    response = await agg.build("proj-123")
    cards = {card.key: card for card in response.cards}
    assert cards["commits_week"].state == "unavailable"
    assert cards["commits_week"].data_origin == "mock"
    assert cards["commits_week"].value is None
