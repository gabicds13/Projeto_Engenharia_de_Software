from __future__ import annotations


def _payload() -> dict:
    return {
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