from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.clients import get_notifications_client
from app.core.config import Settings, get_settings
from app.domain.schemas import Notification, Priority, Source


router = APIRouter(
    prefix="/api/integrations",
    tags=["integrations"],
)


class NotificationInput(BaseModel):
    event_id: str
    project_id: str
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

    notification = Notification(
        
        id=str(uuid4()),
        event_id=data.event_id,
        project_id=data.project_id,
        source=data.source,
        type=data.type,
        priority=data.priority,
        relevance_score=0.5,
        reason="Notificação recebida por integração externa.",
        classified_by="rules",
        title=data.title,
        body=data.body,
        link=data.link,
        created_at=datetime.now(timezone.utc),
        read_at=None,
    )

    client = get_notifications_client()
    return await client.publish(notification)