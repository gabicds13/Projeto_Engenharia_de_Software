"""Testes sem chamadas externas para integração MackAI (Módulo 7)."""
from __future__ import annotations

import httpx
import pytest

from app.clients.mackai_client import MackaiUnavailable, fetch_mackai_metrics
from app.core.config import get_settings
from app.dashboard import router as dashboard_router
from app.domain.schemas import MackaiMetrics

from test_dashboard_api import _token


def _metrics(project_id: str = "proj-123") -> dict:
    return {
        "project_id": project_id,
        "conversations": 12,
        "users": 4,
        "questions": 57,
        "answers_up": 21,
        "answers_down": 3,
        "answers_not_grounded": 6,
        "last_question_at": "2026-11-14T22:24:53Z",
    }


@pytest.mark.asyncio
async def test_mackai_cliente_envia_bearer_apenas_no_header(monkeypatch):
    real_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/projects/proj-123/metrics"
        assert "token" not in str(request.url)
        assert request.headers["authorization"] == "Bearer teste-validado"
        return httpx.Response(200, json=_metrics())

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )
    metrics = await fetch_mackai_metrics(
        base_url="https://mackai.example/",
        project_id="proj-123",
        access_token="teste-validado",
        timeout=2,
    )
    assert metrics.questions == 57


@pytest.mark.asyncio
async def test_mackai_rejeita_resposta_de_outro_projeto(monkeypatch):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=_metrics("outro-projeto"))
            ),
            **kwargs,
        ),
    )
    with pytest.raises(MackaiUnavailable):
        await fetch_mackai_metrics(
            base_url="https://mackai.example",
            project_id="proj-123",
            access_token="teste",
            timeout=2,
        )


@pytest.mark.asyncio
async def test_mackai_rejeita_payload_incompleto(monkeypatch):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"project_id": "proj-123"})
            ),
            **kwargs,
        ),
    )
    with pytest.raises(MackaiUnavailable):
        await fetch_mackai_metrics(
            base_url="https://mackai.example",
            project_id="proj-123",
            access_token="teste",
            timeout=2,
        )


def test_dashboard_mackai_desligado_por_padrao(client):
    response = client.get(
        "/api/bff/dashboard",
        params={"project_id": "proj-123"},
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 200
    assert response.json()["mackai"] == {"state": "disabled", "metrics": None}


def test_dashboard_mackai_funciona_sem_afetar_outros_cards(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "mackai_metrics_enabled", True)

    async def fake_metrics(**kwargs):
        assert kwargs["project_id"] == "proj-123"
        assert kwargs["access_token"]
        return MackaiMetrics.model_validate(_metrics())

    monkeypatch.setattr(dashboard_router, "fetch_mackai_metrics", fake_metrics)
    response = client.get(
        "/api/bff/dashboard",
        params={"project_id": "proj-123"},
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mackai"]["state"] == "ok"
    assert body["mackai"]["metrics"]["questions"] == 57
    assert body["weekly"]["state"] == "ok"
    assert len(body["cards"]) == 4


def test_dashboard_mackai_fora_do_ar_nao_derruba_dashboard(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "mackai_metrics_enabled", True)

    async def offline(**kwargs):
        raise MackaiUnavailable("sem acesso")

    monkeypatch.setattr(dashboard_router, "fetch_mackai_metrics", offline)
    response = client.get(
        "/api/bff/dashboard",
        params={"project_id": "proj-123"},
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mackai"] == {"state": "unavailable", "metrics": None}
    assert len(body["cards"]) == 4


def test_dashboard_usuario_sem_projeto_nao_consulta_mackai(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "mackai_metrics_enabled", True)

    async def should_not_run(**kwargs):
        raise AssertionError("MackAI não pode ser consultado sem acesso ao projeto")

    monkeypatch.setattr(dashboard_router, "fetch_mackai_metrics", should_not_run)
    response = client.get(
        "/api/bff/dashboard",
        params={"project_id": "proj-999"},
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 403
