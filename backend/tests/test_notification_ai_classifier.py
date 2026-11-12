"""Classificador de notificações: regras, LLM opcional e isolamento do contrato externo."""
from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import Settings
from app.domain.schemas import Priority, Source
from app.notifications.classifier import (
    classify_notification,
    rule_based_classification,
)


def _settings(**updates):
    return Settings(
        _env_file=None,
        notification_ai_enabled=False,
        notification_ai_api_key=None,
        notification_ai_model=None,
        **updates,
    )


def test_classificacao_local_prioriza_alerta_de_seguranca():
    result = rule_based_classification(
        source=Source.CODE_REVIEW,
        event_type="review.completed",
        title="Credencial exposta no PR",
        body="Revisão encontrou segredo no repositório",
        incoming_priority=Priority.LOW,
    )
    assert result.priority == Priority.CRITICAL
    assert result.relevance_score >= 0.9
    assert result.classified_by == "rules"


def test_classificacao_local_preserva_prioridade_critica_do_produtor():
    result = rule_based_classification(
        source=Source.RELATORIOS,
        event_type="report.generated",
        title="Relatório",
        body="Foi gerado um relatório.",
        incoming_priority=Priority.CRITICAL,
    )
    assert result.priority == Priority.CRITICAL


def test_classificacao_local_reduz_ruido_informativo():
    result = rule_based_classification(
        source=Source.CURADORIA,
        event_type="curation.recommended",
        title="Novo artigo",
        body="Sugestão de leitura para a equipe.",
        incoming_priority=Priority.MEDIUM,
    )
    assert result.priority == Priority.LOW
    assert "curadoria" in result.reason


@pytest.mark.asyncio
async def test_sem_modelo_usa_regras_sem_chamar_rede(monkeypatch):
    async def should_not_call(*args, **kwargs):
        raise AssertionError("Não deveria consultar provedor de IA")

    monkeypatch.setattr(httpx.AsyncClient, "post", should_not_call)
    result = await classify_notification(
        source=Source.GITHUB,
        event_type="build.failed",
        title="Build failed",
        body="Pipeline bloqueada.",
        incoming_priority=Priority.LOW,
        settings=_settings(),
    )
    assert result.priority == Priority.HIGH
    assert result.classified_by == "rules"


@pytest.mark.asyncio
async def test_modelo_retorna_classificacao_e_nao_recebe_segredos(monkeypatch):
    request_seen = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {"message": {"content": json.dumps({
                        "priority": "high",
                        "relevance_score": 0.91,
                        "reason": "Bloqueio de entrega detectado.",
                    })}}
                ]
            }

    async def fake_post(self, url, headers, json):
        request_seen["url"] = url
        request_seen["headers"] = headers
        request_seen["body"] = json
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    settings = Settings(
        _env_file=None,
        notification_ai_enabled=True,
        notification_ai_api_key="secret-value-test",
        notification_ai_model="modelo-de-teste",
        notification_ai_base_url="https://example.invalid/v1",
    )
    result = await classify_notification(
        source=Source.BACKLOG,
        event_type="story.blocked",
        title="Tarefa bloqueada",
        body="Precisa de aprovação.",
        incoming_priority=Priority.MEDIUM,
        settings=settings,
    )
    assert result.classified_by == "llm"
    assert result.priority == Priority.HIGH
    assert result.relevance_score == 0.91
    assert request_seen["headers"]["Authorization"] == "Bearer secret-value-test"
    sent = request_seen["body"]["messages"][1]["content"]
    assert "secret-value-test" not in sent
    assert "target_user_id" not in sent


@pytest.mark.asyncio
async def test_falha_do_modelo_nao_bloqueia_evento(monkeypatch):
    async def fake_post(self, *args, **kwargs):
        raise httpx.ConnectError("Serviço indisponível")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    settings = Settings(
        _env_file=None,
        notification_ai_enabled=True,
        notification_ai_api_key="test-secret",
        notification_ai_model="teste",
    )
    result = await classify_notification(
        source=Source.CODE_REVIEW,
        event_type="review.security",
        title="Vulnerabilidade crítica",
        body="Problema grave de segurança.",
        incoming_priority=Priority.LOW,
        settings=settings,
    )
    assert result.classified_by == "rules"
    assert result.priority == Priority.CRITICAL


@pytest.mark.asyncio
async def test_modelo_nao_pode_rebaixar_prioridade_do_produtor(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": json.dumps({
                    "priority": "low",
                    "relevance_score": 0.1,
                    "reason": "Baixa relevância aparente.",
                })}}]
            }

    async def fake_post(self, *args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    settings = Settings(
        _env_file=None,
        notification_ai_enabled=True,
        notification_ai_api_key="test-secret",
        notification_ai_model="teste",
    )
    result = await classify_notification(
        source=Source.CODE_REVIEW,
        event_type="review.completed",
        title="Revisão importante",
        body="Atualização.",
        incoming_priority=Priority.CRITICAL,
        settings=settings,
    )
    assert result.priority == Priority.CRITICAL
    assert result.relevance_score >= 0.97


def test_groqcloud_default_eh_desligado_sem_chave():
    """Preparar o provedor não ativa chamadas externas sem autorização."""
    settings = Settings(_env_file=None)
    assert settings.notification_ai_enabled is False
    assert settings.notification_ai_api_key is None
    assert settings.notification_ai_base_url == "https://api.groq.com/openai/v1"
    assert settings.notification_ai_model == "openai/gpt-oss-20b"


@pytest.mark.asyncio
async def test_groqcloud_url_e_contrato_json(monkeypatch):
    """O cliente existente já conversa com a API compatível do Groq."""
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [{"message": {"content": json.dumps({
                    "priority": "medium",
                    "relevance_score": 0.77,
                    "reason": "Mudança relevante para desenvolvedores.",
                })}}]
            }

    async def fake_post(self, url, headers, json):
        captured["url"] = url
        captured["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    settings = Settings(
        _env_file=None,
        notification_ai_enabled=True,
        notification_ai_api_key="chave-ficticia-para-teste",
    )
    result = await classify_notification(
        source=Source.GITHUB,
        event_type="commit.pushed",
        title="Atualização do repositório",
        body="Um commit foi enviado.",
        incoming_priority=Priority.LOW,
        settings=settings,
    )
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["payload"]["model"] == "openai/gpt-oss-20b"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert result.classified_by == "llm"
    assert result.relevance_score == 0.77
