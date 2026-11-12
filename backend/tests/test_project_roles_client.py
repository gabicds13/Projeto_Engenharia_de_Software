"""Integração de papéis reais por projeto com o Módulo 1."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.clients.project_roles_client import _cached_roles, get_project_roles
from app.core.config import Settings
from app.core.security import CurrentUser, Role
from app.domain.schemas import Notification, NotificationPage, Priority, Source
from app.notifications.personalization import (
    personalize_for_project_roles,
    personalize_page_for_projects,
)


@pytest.fixture(autouse=True)
def reset_cache():
    _cached_roles.clear()
    yield
    _cached_roles.clear()


def current_user() -> CurrentUser:
    return CurrentUser(
        user_id="user-1",
        role=None,
        project_ids=("project-A", "project-B"),
        access_token="jwt-placeholder-for-test",
    )


def settings() -> Settings:
    return Settings(_env_file=None, use_mocks=False)


def notification(project_id: str, source: Source = Source.CODE_REVIEW) -> Notification:
    return Notification(
        id=f"notification-{project_id}",
        project_id=project_id,
        source=source,
        type="review.completed",
        priority=Priority.MEDIUM,
        relevance_score=0.5,
        reason="Evento de origem.",
        classified_by="rules",
        title="Revisão",
        body="Revisão concluída.",
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_ler_perfis_reais_e_diferenciar_por_projeto(monkeypatch):
    requests = []

    class Response:
        status_code = 200

        def __init__(self, roles):
            self.roles = roles

        def json(self):
            return {
                "items": [
                    {
                        "user_id": "user-1",
                        "roles": self.roles,
                        "expires_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
                        "is_owner": False,
                    }
                ],
                "total": 1,
            }

    async def fake_get(self, url, **kwargs):
        requests.append((url, kwargs))
        return Response(["Desenvolvedor"] if "project-A" in url else ["Product Owner"])

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    user = current_user()
    a = await get_project_roles("project-A", user, settings())
    b = await get_project_roles("project-B", user, settings())
    assert a == (Role.DEV,)
    assert b == (Role.PO,)
    assert len(requests) == 2
    assert requests[0][1]["headers"]["Authorization"] == "Bearer jwt-placeholder-for-test"

    first = personalize_for_project_roles(notification("project-A"), user, {"project-A": a})
    second = personalize_for_project_roles(notification("project-B"), user, {"project-B": b})
    assert first.personal_relevance_score > second.personal_relevance_score
    assert first.personal_reason.startswith("Para DEV")


@pytest.mark.asyncio
async def test_proprietario_nao_vira_po_sem_atribuicao(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            return {"items": [{"user_id": "user-1", "roles": [], "is_owner": True}], "total": 1}

    async def fake_get(self, url, **kwargs):
        return Response()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    roles = await get_project_roles("project-A", current_user(), settings())
    assert roles == ()
    result = personalize_for_project_roles(
        notification("project-A"), current_user(), {"project-A": roles}
    )
    assert result.personal_relevance_score == 0.5
    assert result.personal_reason is None


@pytest.mark.asyncio
async def test_falha_api_preserva_relevancia_geral(monkeypatch):
    async def fake_get(self, url, **kwargs):
        raise httpx.ConnectError("Serviço indisponível")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    roles = await get_project_roles("project-A", current_user(), settings())
    assert roles is None
    result = personalize_for_project_roles(
        notification("project-A"), current_user(), {"project-A": roles}
    )
    assert result.personal_relevance_score == 0.5


@pytest.mark.asyncio
async def test_perfil_expirado_nao_e_aplicado(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            return {
                "items": [{
                    "user_id": "user-1",
                    "roles": ["DEV"],
                    "expires_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                }],
                "total": 1,
            }

    async def fake_get(self, url, **kwargs):
        return Response()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    assert await get_project_roles("project-A", current_user(), settings()) == ()


def test_papeis_multiplos_usam_maior_relevancia():
    user = current_user()
    n = notification("project-A", Source.GITHUB)
    personalized = personalize_page_for_projects(
        NotificationPage(items=[n]), user, {"project-A": (Role.PO, Role.PM, Role.DEV)}
    )
    assert personalized.items[0].personal_relevance_score == 0.64
    assert n.personal_relevance_score is None
