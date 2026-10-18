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
