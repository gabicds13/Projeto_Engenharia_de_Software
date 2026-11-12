from __future__ import annotations


def _payload() -> dict:
    return {
        "event_id": "test-event-001",
        "project_id": "proj-123",
        "source": "code_review",
        "type": "review.completed",
        "title": "Code review concluído",
        "body": "Teste da API de integração.",
        "priority": "high",
        "link": None,
    }


def test_publish_notification_with_valid_key(client):
    response = client.post(
        "/api/integrations/notifications",
        headers={
            "X-Integration-Key": "dev-integration-key",
        },
        json=_payload(),
    )

    assert response.status_code == 200

    body = response.json()
    assert body["project_id"] == "proj-123"
    assert body["source"] == "code_review"
    assert body["priority"] == "high"


def test_publish_notification_with_invalid_key(client):
    response = client.post(
        "/api/integrations/notifications",
        headers={
            "X-Integration-Key": "chave-errada",
        },
        json=_payload(),
    )

    assert response.status_code == 401

def test_publish_notification_records_llm_classification(client, monkeypatch):
    """O endpoint mantém contrato e grava a classificação fornecida pelo modelo."""
    from app.domain.schemas import Priority
    from app.notifications.classifier import Classification
    import app.api.integrations as integrations

    async def fake_classifier(**kwargs):
        assert kwargs["incoming_priority"] == Priority.HIGH
        return Classification(
            priority=Priority.HIGH,
            relevance_score=0.92,
            reason="Revisão importante segundo o modelo.",
            classified_by="llm",
        )

    monkeypatch.setattr(integrations, "classify_notification", fake_classifier)
    response = client.post(
        "/api/integrations/notifications",
        headers={"X-Integration-Key": "dev-integration-key"},
        json={**_payload(), "event_id": "test-event-llm-001"},
    )
    assert response.status_code == 200
    notification = response.json()
    assert notification["priority"] == "high"
    assert notification["relevance_score"] == 0.92
    assert notification["classified_by"] == "llm"
    assert notification["reason"] == "Revisão importante segundo o modelo."


def test_invalid_key_does_not_invoke_llm(client, monkeypatch):
    """Não há consulta externa antes da validação da chave de integração."""
    import app.api.integrations as integrations

    async def forbidden_classifier(**kwargs):
        raise AssertionError("A IA não pode ser chamada com chave inválida")

    monkeypatch.setattr(integrations, "classify_notification", forbidden_classifier)
    response = client.post(
        "/api/integrations/notifications",
        headers={"X-Integration-Key": "invalid-integration-key"},
        json={**_payload(), "event_id": "test-event-unauthorized"},
    )
    assert response.status_code == 401
