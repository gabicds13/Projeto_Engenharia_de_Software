"""Prévia de IA com RBAC confirmado pelo Módulo 1, sem persistência."""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

import app.notifications.router as notifications_router
from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, Role, get_current_user
from app.main import create_app
from app.notifications.classifier import Classification
from app.domain.schemas import Priority


@pytest.fixture
def preview_client():
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        use_module1_roles=True,
        notification_ai_enabled=False,
        notification_ai_api_key=None,
        use_notifications_db=False,
    )
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="teste-dev",
        role=Role.PO,  # Não equivale a um papel confirmado no Módulo 1.
        project_ids=("projeto-autorizado",),
        access_token="jwt-ficticio-apenas-testes",
    )
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def payload():
    return {
        "project_id": "projeto-autorizado",
        "source": "github",
        "event_type": "pull_request.opened",
        "title": "PR fictício aguardando revisão",
        "body": "Alteração de testes no backend.",
        "priority": "medium",
        "stack": ["Python", "FastAPI"],
        "changed_files": ["tests/exemplo.py"],
    }


def fake_result():
    return Classification(
        priority=Priority.HIGH,
        relevance_score=0.75,
        reason="Alteração requer revisão.",
        classified_by="rules",
        summary="Revisão técnica pendente.",
        group_key="code-review",
    )


def test_envia_ao_classificador_apenas_papel_confirmado(preview_client, monkeypatch):
    captured = {}

    async def fake_roles(project_id, user, settings):
        assert project_id == "projeto-autorizado"
        assert user.user_id == "teste-dev"
        return (Role.DEV,)

    async def fake_classifier(**kwargs):
        captured.update(kwargs)
        return fake_result()

    monkeypatch.setattr(notifications_router, "get_project_roles", fake_roles)
    monkeypatch.setattr(notifications_router, "classify_notification", fake_classifier)
    response = preview_client.post("/api/bff/notifications/context-preview", json=payload())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["roles_verified"] is True
    assert data["verified_roles"] == ["DEV"]
    assert captured["verified_roles"] == (Role.DEV,)
    assert captured["stack"] == ("Python", "FastAPI")
    assert captured["changed_files"] == ("tests/exemplo.py",)
    assert data["notification"]["personal_relevance_score"] > 0.75
    assert data["notification"]["personal_reason"].startswith("Para DEV:")
    assert data["notification"]["summary"] == "Revisão técnica pendente."
    assert data["notification"]["group_key"] == "code-review"


def test_nao_confirma_papel_diante_de_falha_do_modulo1(preview_client, monkeypatch):
    captured = {}

    async def fake_roles(*args, **kwargs):
        return None

    async def fake_classifier(**kwargs):
        captured.update(kwargs)
        return fake_result()

    monkeypatch.setattr(notifications_router, "get_project_roles", fake_roles)
    monkeypatch.setattr(notifications_router, "classify_notification", fake_classifier)
    response = preview_client.post("/api/bff/notifications/context-preview", json=payload())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["roles_verified"] is False
    assert data["verified_roles"] == []
    assert captured["verified_roles"] == ()
    assert data["notification"]["personal_relevance_score"] == 0.75
    assert data["notification"]["personal_reason"] is None


def test_conta_proprietaria_sem_papel_nao_vira_po(preview_client, monkeypatch):
    async def fake_roles(*args, **kwargs):
        return ()

    async def fake_classifier(**kwargs):
        assert kwargs["verified_roles"] == ()
        return fake_result()

    monkeypatch.setattr(notifications_router, "get_project_roles", fake_roles)
    monkeypatch.setattr(notifications_router, "classify_notification", fake_classifier)
    response = preview_client.post("/api/bff/notifications/context-preview", json=payload())
    assert response.status_code == 200, response.text
    assert response.json()["roles_verified"] is True
    assert response.json()["verified_roles"] == []
    assert response.json()["notification"]["personal_relevance_score"] == 0.75


def test_nao_permite_uso_de_papeis_forjados_no_payload(preview_client, monkeypatch):
    async def forbidden_classifier(**kwargs):
        raise AssertionError("A chamada não deve acontecer")

    monkeypatch.setattr(notifications_router, "classify_notification", forbidden_classifier)
    response = preview_client.post(
        "/api/bff/notifications/context-preview",
        json={**payload(), "verified_roles": ["PO"]},
    )
    assert response.status_code == 422


def test_nao_executa_ia_para_projeto_inacessivel(preview_client, monkeypatch):
    async def forbidden_classifier(**kwargs):
        raise AssertionError("A chamada não deve acontecer")

    monkeypatch.setattr(notifications_router, "classify_notification", forbidden_classifier)
    response = preview_client.post(
        "/api/bff/notifications/context-preview",
        json={**payload(), "project_id": "outro-projeto"},
    )
    assert response.status_code == 403


def test_nao_salva_notificacao_no_banco(preview_client, monkeypatch):
    async def fake_roles(*args, **kwargs):
        return (Role.PM,)

    async def fake_classifier(**kwargs):
        return fake_result()

    monkeypatch.setattr(notifications_router, "get_project_roles", fake_roles)
    monkeypatch.setattr(notifications_router, "classify_notification", fake_classifier)
    # O teste fica desconectado de get_notifications_client e do Neon.
    monkeypatch.setattr(
        notifications_router,
        "get_notifications_client",
        lambda: (_ for _ in ()).throw(AssertionError("Não usar banco")),
    )
    response = preview_client.post("/api/bff/notifications/context-preview", json=payload())
    assert response.status_code == 200, response.text
