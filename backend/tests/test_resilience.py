"""Testes da camada de resiliência (Requisitos 6.1, 6.2)."""
from __future__ import annotations

import asyncio

import pytest

from app.core.resilience import (
    ResilienceRegistry,
    UpstreamUnavailable,
)


def make_registry(**overrides) -> ResilienceRegistry:
    defaults = dict(
        timeout_seconds=0.1,
        fails_to_open=3,
        reset_seconds=10.0,
        cache_ttl_seconds=30.0,
    )
    defaults.update(overrides)
    return ResilienceRegistry(**defaults)


async def test_success_returns_value_and_not_stale():
    reg = make_registry()

    async def ok():
        return {"n": 1}

    result = await reg.guarded_call("k", ok)
    assert result.value == {"n": 1}
    assert result.stale is False


async def test_failure_with_cache_returns_stale():
    reg = make_registry()
    calls = {"n": 0}

    async def sometimes():
        calls["n"] += 1
        if calls["n"] == 1:
            return "fresh"
        raise RuntimeError("boom")

    first = await reg.guarded_call("k", sometimes)
    assert first.value == "fresh" and first.stale is False

    second = await reg.guarded_call("k", sometimes)
    assert second.value == "fresh"
    assert second.stale is True  # servido do cache por falha do upstream


async def test_failure_without_cache_raises_unavailable():
    reg = make_registry()

    async def fail():
        raise RuntimeError("down")

    with pytest.raises(UpstreamUnavailable):
        await reg.guarded_call("k", fail)


async def test_timeout_counts_as_failure_and_falls_back():
    reg = make_registry(timeout_seconds=0.05)

    async def seed():
        return "cached"

    await reg.guarded_call("k", seed)

    async def slow():
        await asyncio.sleep(0.2)
        return "late"

    result = await reg.guarded_call("k", slow)
    assert result.value == "cached"
    assert result.stale is True


async def test_breaker_opens_after_n_failures():
    reg = make_registry(fails_to_open=2, reset_seconds=10.0)
    probe = {"calls": 0}

    async def fail():
        probe["calls"] += 1
        raise RuntimeError("down")

    # Sem cache: cada falha levanta, mas conta no breaker.
    for _ in range(2):
        with pytest.raises(UpstreamUnavailable):
            await reg.guarded_call("k", fail)

    # Breaker aberto: a próxima chamada nem executa a factory.
    calls_before = probe["calls"]
    with pytest.raises(UpstreamUnavailable):
        await reg.guarded_call("k", fail)
    assert probe["calls"] == calls_before  # factory não foi chamada
