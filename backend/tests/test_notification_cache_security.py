"""Regressões de isolamento dos dados em cache e permissões da API."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import jwt
import pytest

from app.core.config import get_settings
from app.core.resilience import get_registry
from app.domain.schemas import NotificationPage
from app.notifications.router import _notification_cache_key


@pytest.fixture(autouse=True)
def reset_cache():
    from app import clients

    get_registry.cache_clear()
    clients.get_notifications_client.cache_clear()
    yield
    get_registry.cache_clear()
    clients.get_notifications_client.cache_clear()


def _auth(project_ids: tuple[str, ...], user_id: str = "user-1") -> dict[str, str]:
    settings = get_settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": user_id,
            "role": "DEV",
            "project_ids": list(project_ids),
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def test_cache_distingue_projetos_e_filtros():
    from app.core.security import CurrentUser, Role

    a = CurrentUser(user_id="u", role=Role.DEV, project_ids=("a",))
    b = CurrentUser(user_id="u", role=Role.DEV, project_ids=("b",))
    assert _notification_cache_key("list", a, status=None, limit=20) != (
        _notification_cache_key("list", b, status=None, limit=20)
    )
    assert _notification_cache_key("list", a, status="read", limit=20) != (
        _notification_cache_key("list", a, status="unread", limit=20)
    )
    assert _notification_cache_key("list", a, status=None, limit=20) != (
        _notification_cache_key("list", a, status=None, limit=10)
    )


def test_cache_nao_retorna_notificacoes_apos_mudanca_de_projetos(client, monkeypatch):
    import app.notifications.router as notification_router

    class FailingAfterFirst:
        calls = 0

        async def list(self, user, **kwargs):
            self.calls += 1
            if self.calls > 1:
                raise ConnectionError("notificacoes indisponiveis")
            return NotificationPage(items=[])

    fake = FailingAfterFirst()
    monkeypatch.setattr(notification_router, "get_notifications_client", lambda: fake)
    get_registry()._cache.clear()
    get_registry()._breakers.clear()

    first = client.get("/api/bff/notifications", headers=_auth(("proj-a",)))
    assert first.status_code == 200
    assert first.json()["state"] == "ok"

    second = client.get("/api/bff/notifications", headers=_auth(("proj-b",)))
    assert second.status_code == 200
    assert second.json()["state"] == "unavailable"
    assert fake.calls == 2


def test_filtros_nao_reutilizam_cache_de_outra_consulta(client, monkeypatch):
    import app.notifications.router as notification_router

    class FailingAfterFirst:
        calls = 0

        async def list(self, user, **kwargs):
            self.calls += 1
            if self.calls > 1:
                raise ConnectionError("notificacoes indisponiveis")
            return NotificationPage(items=[])

    fake = FailingAfterFirst()
    monkeypatch.setattr(notification_router, "get_notifications_client", lambda: fake)
    get_registry()._cache.clear()
    get_registry()._breakers.clear()

    first = client.get("/api/bff/notifications", params={"status": "read"}, headers=_auth(("proj-a",)))
    second = client.get("/api/bff/notifications", params={"status": "unread"}, headers=_auth(("proj-a",)))
    assert first.status_code == 200 and first.json()["state"] == "ok"
    assert second.status_code == 200 and second.json()["state"] == "unavailable"


def test_marcar_como_lida_invalida_todos_filtros(client):
    from app.core.resilience import get_registry

    headers = _auth(("proj-123",))
    assert client.get("/api/bff/notifications", params={"status": "unread"}, headers=headers).status_code == 200
    assert client.get("/api/bff/notifications", params={"status": "read"}, headers=headers).status_code == 200
    assert client.get("/api/bff/notifications/unread-count", headers=headers).status_code == 200

    reg = get_registry()
    prefixes = ("notifications:list:user-1:", "notifications:unread:user-1:")
    assert any(key.startswith(prefixes) for key in reg._cache)

    assert client.post("/api/bff/notifications/read-all", headers=headers).status_code == 200
    assert not any(key.startswith(prefixes) for key in reg._cache)
