"""Testes de contrato, segurança e disponibilidade da integração M4."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from base64 import b64encode

import httpx
import pytest
from jose import jwt

from app.api import code_reviews as m4_router
from app.clients.code_review_client import (
    CodeReviewUnavailable,
    HttpCodeReviewClient,
    project_repository_names,
)
from app.core.config import get_settings


def _token(project_ids=("proj-123",)):
    s = get_settings()
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": "m4-user",
            "role": "DEV",
            "project_ids": list(project_ids),
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        s.jwt_secret,
        algorithm=s.jwt_algorithm,
    )


def _entry(url, *, ident="review-1"):
    return {
        "id": ident,
        "criado_em": "2026-11-15T12:00:00+00:00",
        "arquitetura": "multicamadas",
        "pr": {"url": url, "sha": "a" * 40},
        "achados": [
            {"arquivo": "app.py", "linha": 1, "gravidade": "Alta",
             "titulo": "Exemplo", "sugestao": "Remover"}
        ],
        "markdown": "texto completo privado nao deve ser exposto",
        "ia": {"texto": "resposta completa"},
    }


def _mock_http(monkeypatch, handler):
    async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: async_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )


@pytest.mark.asyncio
async def test_m4_client_filtra_repositorios_e_nao_retorna_conteudo_privado(monkeypatch):
    auth = "Basic " + b64encode(b"revisor:senha-de-teste").decode()

    def handler(req):
        assert req.url.host == "m4.example"
        assert req.url.path == "/api/historico"
        assert req.headers["authorization"] == auth
        return httpx.Response(200, json=[
            _entry("https://github.com/equipe/autorizado/pull/15"),
            _entry("https://github.com/equipe/privado/pull/99", ident="review-2"),
            _entry("https://github.com/equipe/autorizado/pull/16", ident="review-3")
            | {"pr": None},
        ])

    _mock_http(monkeypatch, handler)
    results = await HttpCodeReviewClient(
        base_url="https://m4.example", username="revisor",
        password="senha-de-teste", timeout=2,
    ).history({"equipe/autorizado"})
    assert len(results) == 1
    assert results[0]["findings_count"] == 1
    assert results[0]["severity_counts"] == {"Alta": 1}
    assert "markdown" not in results[0]
    assert "ia" not in results[0]
    assert "achados" not in results[0]


@pytest.mark.asyncio
async def test_m4_busca_repositorios_somente_do_projeto_autorizado(monkeypatch):
    def handler(req):
        assert req.url.host == "m2.example"
        assert req.url.path == "/api/v1/repositories"
        assert req.url.params["project_id"] == "proj-123"
        assert req.headers["authorization"] == "Bearer token-de-teste"
        return httpx.Response(200, json=[
            {"id": 1, "project_id": "proj-123",
             "full_name": "Equipe/Repositorio"}
        ])

    _mock_http(monkeypatch, handler)
    repos = await project_repository_names(
        github_url="https://m2.example", project_id="proj-123",
        access_token="token-de-teste", timeout=2,
    )
    assert repos == {"equipe/repositorio"}


@pytest.mark.asyncio
async def test_m4_rejeita_repositorios_de_outro_projeto(monkeypatch):
    _mock_http(monkeypatch, lambda _: httpx.Response(
        200, json=[{"id": 1, "project_id": "outro",
                    "full_name": "equipe/privado"}],
    ))
    with pytest.raises(CodeReviewUnavailable):
        await project_repository_names(
            github_url="https://m2.example", project_id="proj-123",
            access_token="token-de-teste", timeout=2,
        )


@pytest.mark.asyncio
async def test_m4_rejeita_falha_de_autenticacao_basica(monkeypatch):
    _mock_http(monkeypatch, lambda _: httpx.Response(401, json={"erro": "negado"}))
    with pytest.raises(CodeReviewUnavailable):
        await HttpCodeReviewClient(
            base_url="https://m4.example", username="revisor",
            password="senha-de-teste", timeout=2,
        ).history({"equipe/autorizado"})


@pytest.mark.asyncio
async def test_m4_rejeita_historico_truncado_ou_formato_errado(monkeypatch):
    _mock_http(monkeypatch, lambda _: httpx.Response(200, json=[{}] * 21))
    with pytest.raises(CodeReviewUnavailable):
        await HttpCodeReviewClient(
            base_url="https://m4.example", username="revisor",
            password="senha-de-teste", timeout=2,
        ).history({"equipe/autorizado"})


def test_m4_rota_exige_login(client):
    assert client.get("/api/bff/code-reviews", params={"project_id": "proj-123"}).status_code == 401


def test_m4_rota_rejeita_outro_projeto_sem_consultar_m4(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "code_review_enabled", True)
    monkeypatch.setattr(settings, "code_review_password", "senha-de-teste")

    async def forbidden_upstream(**_):
        raise AssertionError("Nao deveria chamar o modulo externo")

    monkeypatch.setattr(m4_router, "project_repository_names", forbidden_upstream)
    response = client.get(
        "/api/bff/code-reviews", params={"project_id": "outro"},
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 403


def test_m4_rota_desligada_por_padrao(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "code_review_enabled", False)
    response = client.get(
        "/api/bff/code-reviews", params={"project_id": "proj-123"},
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 503


def test_m4_rota_isola_dados_e_nao_expõe_senha(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "code_review_enabled", True)
    monkeypatch.setattr(settings, "code_review_password", "senha-super-secreta")
    monkeypatch.setattr(settings, "github_url", "https://m2.example")

    async def repos(**kwargs):
        assert kwargs["project_id"] == "proj-123"
        assert kwargs["access_token"]
        return {"equipe/autorizado"}

    async def history(self, allowed):
        assert allowed == {"equipe/autorizado"}
        return [{"id": "review-1", "pr_url": "https://github.com/equipe/autorizado/pull/1"}]

    monkeypatch.setattr(m4_router, "project_repository_names", repos)
    monkeypatch.setattr(m4_router.HttpCodeReviewClient, "history", history)
    response = client.get(
        "/api/bff/code-reviews", params={"project_id": "proj-123"},
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["history_limited"] is True
    assert body["pending_reviews"] is None
    assert len(body["items"]) == 1
    assert "senha-super-secreta" not in response.text


def test_m4_rota_indisponivel_sem_retorno_de_outro_servico(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "code_review_enabled", True)
    monkeypatch.setattr(settings, "code_review_password", "senha-de-teste")
    monkeypatch.setattr(settings, "github_url", "https://m2.example")

    async def unavailable(**_):
        raise CodeReviewUnavailable("servico falhou")

    monkeypatch.setattr(m4_router, "project_repository_names", unavailable)
    response = client.get(
        "/api/bff/code-reviews", params={"project_id": "proj-123"},
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 503
    assert "servico falhou" not in response.text
