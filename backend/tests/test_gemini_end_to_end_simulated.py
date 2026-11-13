"""Fluxo completo: evento HTTP -> Gemini simulado -> SQLite isolado -> BFF.

Nenhuma chamada chega à API real, ao Neon nem ao Módulo 1.
"""
from __future__ import annotations

import json

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.integrations as integrations
import app.clients.database_notifications_client as database_notifications
import app.notifications.router as notifications_router
from app.clients.database_notifications_client import DatabaseNotificationsClient
from app.core.config import Settings, get_settings
from app.core.resilience import ResilienceRegistry
from app.core.security import CurrentUser, get_current_user
from app.main import create_app
from app.models.notification import NotificationModel
from app.models.notification_read import NotificationReadModel


def test_evento_ia_simulada_armazenado_e_recuperado_sem_neon(monkeypatch):
    """Confere publicação, validação do JSON, persistência e leitura pelo BFF."""
    # Banco exclusivo do teste: nunca lê DATABASE_URL da máquina.
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    NotificationModel.metadata.create_all(
        engine,
        tables=[NotificationModel.__table__, NotificationReadModel.__table__],
    )
    test_session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(
        database_notifications, "get_session_factory", lambda: test_session_factory
    )

    store = DatabaseNotificationsClient()
    monkeypatch.setattr(integrations, "get_notifications_client", lambda: store)
    monkeypatch.setattr(notifications_router, "get_notifications_client", lambda: store)
    monkeypatch.setattr(
        notifications_router,
        "get_registry",
        lambda: ResilienceRegistry(
            timeout_seconds=5,
            fails_to_open=5,
            reset_seconds=10,
            cache_ttl_seconds=1,
        ),
    )

    settings = Settings(
        _env_file=None,
        app_env="development",
        use_mocks=True,
        use_notifications_db=True,
        use_module1_roles=False,
        database_url=None,  # Proteção adicional contra conexão ao Neon.
        notification_ai_enabled=True,
        notification_ai_api_key="somente-chave-ficticia-do-teste",
        notification_ai_model="gemini-2.5-flash-lite",
        notification_ai_base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        integration_api_key="chave-interna-ficticia-do-teste",
    )
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="usuario-teste-local",
        role=None,
        project_ids=("projeto-teste-local",),
    )

    captured = {}

    class FakeGeminiResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {"message": {"content": json.dumps({
                        "priority": "high",
                        "relevance_score": 0.87,
                        "summary": "Pull request aguarda revisão técnica.",
                        "reason": "Alteração relevante exige uma revisão.",
                        "group_key": "code-review",
                    })}}
                ]
            }

    async def fake_gemini_post(self, url, headers=None, json=None, **kwargs):
        captured["url"] = url
        captured["payload"] = json
        captured["api_key"] = headers.get("Authorization")
        return FakeGeminiResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_gemini_post)

    payload = {
        "event_id": "e2e-gemini-simulado-001",
        "project_id": "projeto-teste-local",
        "source": "github",
        "type": "github.pull_request.opened",
        "title": "Pull request pronto para revisão",
        "body": "Mudanças no serviço de notificações precisam de revisão.",
        "priority": "medium",
        "stack": ["Python", "FastAPI"],
        "changed_files": ["app/notifications/router.py"],
    }

    with TestClient(app) as client:
        posted = client.post(
            "/api/integrations/notifications",
            headers={"X-Integration-Key": "chave-interna-ficticia-do-teste"},
            json=payload,
        )
        assert posted.status_code == 200, posted.text
        item = posted.json()
        assert item["classified_by"] == "llm"
        assert item["priority"] == "high"
        assert item["relevance_score"] == 0.87
        assert item["summary"] == "Pull request aguarda revisão técnica."
        assert item["reason"] == "Alteração relevante exige uma revisão."
        assert item["group_key"] == "code-review"
        assert captured["url"] == (
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        )
        assert captured["payload"]["model"] == "gemini-2.5-flash-lite"
        context = json.loads(captured["payload"]["messages"][1]["content"])
        assert context["stack"] == ["Python", "FastAPI"]
        assert context["changed_files"] == ["app/notifications/router.py"]
        assert context["verified_roles"] == []
        assert captured["api_key"] == "Bearer somente-chave-ficticia-do-teste"

        # Uma consulta nova ao SQLite comprova que os campos foram gravados.
        with test_session_factory() as session:
            row = session.scalar(
                select(NotificationModel).where(
                    NotificationModel.event_id == payload["event_id"]
                )
            )
            assert row is not None
            assert row.summary == "Pull request aguarda revisão técnica."
            assert row.group_key == "code-review"
            assert row.classified_by == "llm"

        listed = client.get("/api/bff/notifications")
        assert listed.status_code == 200, listed.text
        assert listed.json()["state"] == "ok"
        notifications = listed.json()["page"]["items"]
        assert len(notifications) == 1
        assert notifications[0]["event_id"] == payload["event_id"]
        assert notifications[0]["classified_by"] == "llm"
        assert notifications[0]["summary"] == "Pull request aguarda revisão técnica."
        assert notifications[0]["group_key"] == "code-review"
        assert notifications[0]["personal_relevance_score"] == 0.87

    engine.dispose()
