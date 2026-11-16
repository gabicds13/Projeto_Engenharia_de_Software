"""Contrato do feed de tendências M5 e proteção da rota BFF."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from jose import jwt

from app.api import curadoria as curadoria_router
from app.clients.curadoria_client import CuradoriaUnavailable, fetch_em_alta
from app.core.config import get_settings


def _token():
    settings = get_settings()
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": "m5-user",
            "role": "DEV",
            "project_ids": ["proj-123"],
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _payload(url="https://arxiv.org/abs/1234.56789"):
    return {
        "total": 1,
        "artigos": [{
            "titulo": "Python e segurança de software",
            "link": url,
            "fonte": "arXiv",
            "idioma": "pt",
            "resumo": "Texto completo não necessário para o Dashboard",
            "data_publicacao": "2026-11-15",
            "categoria": "Desenvolvimento",
            "pontuacao": 94.3,
        }],
        "categorias": [{"nome": "Desenvolvimento", "quantidade": 1}],
        "artigos_analisados": 1,
        "atualizado_em": "2026-11-15T12:00:00+00:00",
        "metodo_ranking": "Recência e relevância",
    }


def _mock_http(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )


@pytest.mark.asyncio
async def test_m5_retorna_artigos_reais_sem_misturar_dados_do_projeto(monkeypatch):
    def handler(req: httpx.Request):
        assert req.url.host == "m5.example"
        assert req.url.path == "/em-alta"
        assert req.url.params["limite"] == "6"
        assert "authorization" not in req.headers
        return httpx.Response(200, json=_payload())

    _mock_http(monkeypatch, handler)
    result = await fetch_em_alta(base_url="https://m5.example", timeout=2)
    assert result["scope"] == "global"
    assert result["articles"] == [{
        "title": "Python e segurança de software",
        "url": "https://arxiv.org/abs/1234.56789",
        "source": "arXiv",
        "category": "Desenvolvimento",
        "published_at": "2026-11-15",
    }]
    assert "resumo" not in str(result)
    assert "pontuacao" not in str(result)


@pytest.mark.asyncio
async def test_m5_rejeita_link_inseguro(monkeypatch):
    _mock_http(monkeypatch, lambda _: httpx.Response(200, json=_payload("javascript:alert(1)")))
    with pytest.raises(CuradoriaUnavailable):
        await fetch_em_alta(base_url="https://m5.example", timeout=2)


@pytest.mark.asyncio
async def test_m5_rejeita_resposta_invalida(monkeypatch):
    _mock_http(monkeypatch, lambda _: httpx.Response(200, json={"artigos": "erro"}))
    with pytest.raises(CuradoriaUnavailable):
        await fetch_em_alta(base_url="https://m5.example", timeout=2)


@pytest.mark.asyncio
async def test_m5_rejeita_http_nao_seguro():
    with pytest.raises(CuradoriaUnavailable):
        await fetch_em_alta(base_url="http://m5.example", timeout=2)


def test_m5_exige_autenticacao(client):
    response = client.get("/api/bff/curadoria/em-alta")
    assert response.status_code == 401


def test_m5_desligado_por_padrao(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "curadoria_enabled", False)
    response = client.get(
        "/api/bff/curadoria/em-alta",
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 503


def test_m5_rota_funciona_com_flag_ativa(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "curadoria_enabled", True)

    async def fake_fetch(**kwargs):
        assert kwargs["limit"] == 6
        return {"source": "module-5", "scope": "global",
                "updated_at": "2026-11-15T12:00:00+00:00", "articles": []}

    monkeypatch.setattr(curadoria_router, "fetch_em_alta", fake_fetch)
    response = client.get(
        "/api/bff/curadoria/em-alta",
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 200
    assert response.json()["scope"] == "global"


def test_m5_fora_do_ar_nao_expoe_erro_interno(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "curadoria_enabled", True)

    async def unavailable(**_):
        raise CuradoriaUnavailable("erro interno privado")

    monkeypatch.setattr(curadoria_router, "fetch_em_alta", unavailable)
    response = client.get(
        "/api/bff/curadoria/em-alta",
        headers={"Authorization": f"Bearer {_token()}"},
    )
    assert response.status_code == 503
    assert "erro interno privado" not in response.text
