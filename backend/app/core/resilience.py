"""Resiliência para chamadas a serviços downstream (degradação graciosa).

`guarded_call` executa uma coroutine com:
  1. timeout explícito;
  2. circuit breaker simples por chave (abre após N falhas, meio-aberto após T);
  3. cache da última resposta válida (TTL).

Em sucesso, devolve `GuardedResult(value, stale=False)` e atualiza o cache.
Em falha (erro, timeout ou breaker aberto), devolve o valor em cache marcado como
`stale=True`, se houver; caso contrário levanta `UpstreamUnavailable`.

Assim, a falha de um serviço de terceiros NUNCA vira um erro de página — vira um
estado parcial que o front-end traduz em "indisponível no momento".
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")


class UpstreamUnavailable(Exception):
    """Serviço downstream indisponível e sem cache para servir."""

    def __init__(self, key: str, reason: str):
        super().__init__(f"upstream '{key}' indisponível: {reason}")
        self.key = key
        self.reason = reason


@dataclass(frozen=True)
class GuardedResult(Generic[T]):
    value: T
    stale: bool  # True quando servido do cache por falha do upstream


class _BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class _CacheEntry:
    value: object
    stored_at: float


class _Breaker:
    def __init__(self, fails_to_open: int, reset_seconds: float):
        self._fails_to_open = fails_to_open
        self._reset_seconds = reset_seconds
        self._consecutive_fails = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> _BreakerState:
        if self._opened_at is None:
            return _BreakerState.CLOSED
        if (time.monotonic() - self._opened_at) >= self._reset_seconds:
            return _BreakerState.HALF_OPEN
        return _BreakerState.OPEN

    def allows_call(self) -> bool:
        return self.state in (_BreakerState.CLOSED, _BreakerState.HALF_OPEN)

    def record_success(self) -> None:
        self._consecutive_fails = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._consecutive_fails += 1
        if self._consecutive_fails >= self._fails_to_open:
            self._opened_at = time.monotonic()


class ResilienceRegistry:
    """Mantém breakers e cache por chave. Uma instância por processo."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        fails_to_open: int,
        reset_seconds: float,
        cache_ttl_seconds: float,
    ):
        self._timeout = timeout_seconds
        self._fails_to_open = fails_to_open
        self._reset_seconds = reset_seconds
        self._cache_ttl = cache_ttl_seconds
        self._breakers: dict[str, _Breaker] = {}
        self._cache: dict[str, _CacheEntry] = {}

    def _breaker(self, key: str) -> _Breaker:
        if key not in self._breakers:
            self._breakers[key] = _Breaker(self._fails_to_open, self._reset_seconds)
        return self._breakers[key]

    def _cached(self, key: str) -> _CacheEntry | None:
        return self._cache.get(key)

    async def guarded_call(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        *,
        timeout: float | None = None,
    ) -> GuardedResult[T]:
        breaker = self._breaker(key)
        timeout = self._timeout if timeout is None else timeout

        if not breaker.allows_call():
            return self._fallback(key, "circuit breaker aberto")

        try:
            value = await asyncio.wait_for(factory(), timeout=timeout)
        except Exception as exc:  # noqa: BLE001 — qualquer falha vira degradação
            breaker.record_failure()
            return self._fallback(key, repr(exc))

        breaker.record_success()
        self._cache[key] = _CacheEntry(value=value, stored_at=time.monotonic())
        return GuardedResult(value=value, stale=False)

    def _fallback(self, key: str, reason: str) -> GuardedResult:
        entry = self._cached(key)
        if entry is not None and (time.monotonic() - entry.stored_at) <= self._cache_ttl:
            return GuardedResult(value=entry.value, stale=True)
        # Mesmo expirado, servir cache antigo é melhor que falhar — mas só se existir.
        if entry is not None:
            return GuardedResult(value=entry.value, stale=True)
        raise UpstreamUnavailable(key, reason)


from functools import lru_cache  # noqa: E402

from app.core.config import get_settings  # noqa: E402


@lru_cache
def get_registry() -> ResilienceRegistry:
    s = get_settings()
    return ResilienceRegistry(
        timeout_seconds=s.upstream_timeout_seconds,
        fails_to_open=s.circuit_breaker_fails,
        reset_seconds=s.circuit_breaker_reset_seconds,
        cache_ttl_seconds=s.cache_ttl_seconds,
    )
