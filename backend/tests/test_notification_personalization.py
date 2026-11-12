"""Personalização por perfil não modifica notificações armazenadas nem permissões."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import CurrentUser, Role
from app.domain.schemas import Notification, NotificationPage, Priority, Source
from app.notifications.personalization import (
    personalize_notification,
    personalize_page,
 )
from app.notifications.router import personalized_ws_source


def notification(
    source: Source,
    priority: Priority = Priority.MEDIUM,
    score: float = 0.5,
    *,
    event_type: str = "example.created",
    id: str = "n1",
) -> Notification:
    return Notification(
        id=id,
        project_id="proj-123",
        source=source,
        type=event_type,
        priority=priority,
        relevance_score=score,
        reason="Prioridade do evento.",
        classified_by="rules",
        title="Notificação de teste",
        body="Conteúdo de teste.",
        created_at=datetime.now(UTC),
    )


def user(role: Role | None) -> CurrentUser:
    return CurrentUser(user_id="u1", role=role, project_ids=("proj-123",))


def test_pontuacao_por_perfil_diferente_na_mesma_notificacao():
    original = notification(Source.CODE_REVIEW)
    dev = personalize_notification(original, user(Role.DEV))
    po = personalize_notification(original, user(Role.PO))

    assert dev.personal_relevance_score > po.personal_relevance_score
    assert dev.personal_reason and "DEV" in dev.personal_reason
    assert original.personal_relevance_score is None


def test_pm_prioriza_backlog_e_po_prioriza_artefatos():
    backlog = notification(Source.BACKLOG)
    artefatos = notification(Source.ARTEFATOS)
    pm = personalize_notification(backlog, user(Role.PM))
    po = personalize_notification(artefatos, user(Role.PO))
    assert pm.personal_relevance_score == 0.66
    assert po.personal_relevance_score == 0.62


def test_sem_perfil_aplica_ordenacao_neutra():
    original = notification(Source.GITHUB, score=0.52)
    result = personalize_notification(original, user(None))
    assert result.personal_relevance_score == 0.52
    assert result.personal_reason is None


def test_prioridade_critica_fica_na_frente_mas_sem_modificar_a_base():
    old = notification(Source.CODE_REVIEW, Priority.CRITICAL, 0.4, id="critical")
    recent = notification(Source.BACKLOG, Priority.LOW, 0.95, id="low")
    page = NotificationPage(items=[recent, old], next_cursor="next-page")
    personalized = personalize_page(page, user(Role.PM))

    assert [n.id for n in personalized.items] == ["critical", "low"]
    assert personalized.next_cursor == "next-page"
    assert page.items[0].id == "low"


def test_ordenacao_empata_pela_data():
    now = datetime.now(UTC)
    a = notification(Source.RAG, id="older").model_copy(
        update={"created_at": now - timedelta(minutes=10)}
    )
    b = notification(Source.RAG, id="newer").model_copy(
        update={"created_at": now}
    )
    ordered = personalize_page(NotificationPage(items=[a, b]), user(None))
    assert [item.id for item in ordered.items] == ["newer", "older"]


@pytest.mark.asyncio
async def test_websocket_recebe_pontuacao_do_mesmo_perfil():
    n = notification(Source.CODE_REVIEW)

    async def source():
        yield {"event": "notification.new", "data": n.model_dump(mode="json")}

    events = [event async for event in personalized_ws_source(source(), user(Role.DEV))]
    assert len(events) == 1
    data = events[0]["data"]
    assert data["personal_relevance_score"] == 0.66
    assert data["personal_reason"].startswith("Para DEV:")
