from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.clients import get_notifications_client
from app.notifications.classifier import classify_notification
from app.core.config import Settings, get_settings
from app.domain.schemas import (
    Notification,
    NotificationScope,
    Priority,
    Source,
)

router = APIRouter(
    prefix="/api/integrations",
    tags=["integrations"],
)


class NotificationInput(BaseModel):
    event_id: str
    scope: NotificationScope = NotificationScope.PROJECT
    project_id: str | None = None
    source: Source
    type: str
    title: str
    body: str
    priority: Priority = Priority.MEDIUM
    link: str | None = None


@router.post("/notifications", response_model=Notification)
async def publish_notification(
    data: NotificationInput,
    x_integration_key: str = Header(..., alias="X-Integration-Key"),
    settings: Settings = Depends(get_settings),
) -> Notification:

    if x_integration_key != settings.integration_api_key:
        raise HTTPException(
            status_code=401,
            detail="Chave de integração inválida.",
        )

    if data.scope == NotificationScope.PROJECT and not data.project_id:
        raise HTTPException(
            status_code=422,
            detail="project_id é obrigatório para notificações de projeto.",
        )

    classification = await classify_notification(
        source=data.source,
        event_type=data.type,
        title=data.title,
        body=data.body,
        incoming_priority=data.priority,
        settings=settings,
    )

    notification = Notification(
        id=str(uuid4()),
        event_id=data.event_id,
        scope=data.scope,
        project_id=(
            data.project_id
            if data.scope == NotificationScope.PROJECT
            else None
        ),
        source=data.source,
        type=data.type,
        priority=classification.priority,
        relevance_score=classification.relevance_score,
        reason=classification.reason,
        classified_by=classification.classified_by,
        title=data.title,
        body=data.body,
        link=data.link,
        created_at=datetime.now(UTC),
        read_at=None,
    )

    client = get_notifications_client()

    return await client.publish(notification)