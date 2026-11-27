"""Testes do novo contrato do M4: somente contagens, escopos separados."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
from jose import jwt

from app.core.config import get_settings

PROJECT = "12345678-1234-4abc-9876-123456789abc"
OTHER = "22345678-1234-4abc-9876-123456789abc"
PATH = "/api/bff/code-reviews/metrics"
METRICS = {
    "total_revisoes": 3,
    "total_achados": 7,
    "por_prioridade": {"critical": 1, "high": 2, "medium": 3, "low": 1},
    "por_categoria": {"segurança": 2, "qualidade": 5},
    "por_arquitetura": {"microsserviços": 3},
    "revisoes_por_dia": [{"data": "2026-11-26", "revisoes": 3, "achados": 7}],
}


def _headers(project=PROJECT):
    settings = get_settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "metrics-user", "role": "DEV", "project_ids": [project],
         "iat": now, "exp": now + timedelta(hours=1)},
        settings.jwt_secret, algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": "Bearer " + token}


def _upstream(monkeypatch, handler):
    settings = get_settings()
    monkeypatch.setattr(settings, "code_review_enabled", True)
    monkeypatch.setattr(settings, "code_review_password", None)
    monkeypatch.setattr(settings, "code_review_url", "https://m4.example")
    async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kwargs: async_client(transport=httpx.MockTransport(handler), **kwargs),
    )


def test_real_metrics_require_project_and_send_no_credentials(client, monkeypatch):
    def handler(request):
        assert request.url.host == "m4.example"
        assert request.url.path == "/api/dashboard/metricas"
        assert dict(request.url.params) == {"project_id": PROJECT, "dias": "30"}
        assert "authorization" not in request.headers
        return httpx.Response(200, json=METRICS | {"project_id": PROJECT, "private_extra": "not forwarded"})

    _upstream(monkeypatch, handler)
    response = client.get(PATH, params={"project_id": PROJECT, "dias": 30}, headers=_headers())
    assert response.status_code == 200
    assert response.json() == {
        "project_id": PROJECT, "scope": "project", "dias": 30, "source": "module-4",
        "data_origin": "real", "metrics": METRICS,
    }


def test_metrics_never_consult_upstream_without_access(client, monkeypatch):
    def unexpected(request):
        raise AssertionError("M4 não deve ser consultado")
    _upstream(monkeypatch, unexpected)
    assert client.get(PATH, params={"project_id": PROJECT}).status_code == 401
    assert client.get(PATH, params={"project_id": OTHER}, headers=_headers()).status_code == 403
    assert client.get(PATH, headers=_headers()).status_code == 422
    for days in (0, 91):
        assert client.get(PATH, params={"project_id": PROJECT, "dias": days}, headers=_headers()).status_code == 422
    assert client.get(PATH, params={"project_id": "invalid"}, headers=_headers()).status_code == 422


def test_metrics_fail_closed_on_invalid_or_unavailable_data(client, monkeypatch):
    for payload, status in (
        (METRICS | {"project_id": OTHER}, 200),
        (METRICS | {"project_id": PROJECT, "total_achados": -1}, 200),
        (METRICS | {"project_id": PROJECT, "por_prioridade": {}}, 200),
        ({}, 503),
        ({}, 200),
    ):
        _upstream(monkeypatch, lambda request, p=payload, s=status: httpx.Response(s, json=p))
        response = client.get(PATH, params={"project_id": PROJECT}, headers=_headers())
        assert response.status_code == 503
        assert "metrics" not in response.json()
        monkeypatch.undo()


def test_global_metrics_are_explicit_and_public_aggregates_only(client, monkeypatch):
    def handler(request):
        assert request.url.path == "/api/dashboard/metricas"
        assert dict(request.url.params) == {"dias": "14"}
        assert "authorization" not in request.headers
        return httpx.Response(200, json=METRICS | {
            "project_id": None, "private_extra": "not forwarded",
        })

    _upstream(monkeypatch, handler)
    response = client.get(PATH + "/global", headers=_headers())
    assert response.status_code == 200
    assert response.json() == {
        "project_id": None, "scope": "global", "dias": 14,
        "source": "module-4", "data_origin": "real", "metrics": METRICS,
    }


def test_global_requires_login_and_valid_period(client, monkeypatch):
    def unexpected(request):
        raise AssertionError("M4 não deve ser consultado")
    _upstream(monkeypatch, unexpected)
    assert client.get(PATH + "/global").status_code == 401
    assert client.get(PATH + "/global", params={"dias": 91}, headers=_headers()).status_code == 422


def test_global_rejects_project_scoped_response(client, monkeypatch):
    _upstream(monkeypatch, lambda request: httpx.Response(200, json=METRICS | {"project_id": PROJECT}))
    assert client.get(PATH + "/global", headers=_headers()).status_code == 503


def test_project_rejects_global_response_and_never_falls_back(client, monkeypatch):
    calls = []
    def handler(request):
        calls.append(dict(request.url.params))
        return httpx.Response(200, json=METRICS | {"project_id": None})
    _upstream(monkeypatch, handler)
    assert client.get(PATH, params={"project_id": PROJECT}, headers=_headers()).status_code == 503
    assert calls == [{"dias": "14", "project_id": PROJECT}]
