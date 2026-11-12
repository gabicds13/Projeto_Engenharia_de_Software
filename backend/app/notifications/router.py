"""Rotas de notificações: proxy REST + WebSocket bridge para o ms-notifications."""
from __future__ import annotations

from dataclasses import replace
from typing import Literal

from fastapi import APIRouter, Depends, Query, WebSocket
from pydantic import BaseModel

from app.clients import get_notifications_client
from app.clients.projects_client import list_accessible_project_ids
from app.core.config import Settings, get_settings
from app.core.resilience import UpstreamUnavailable, get_registry
from app.core.security import (
    CurrentUser,
    get_current_user,
    ws_authenticate_message,
)
from app.core.ws_bridge import pump
from app.notifications.personalization import personalize_page, personalize_notification
from app.domain.schemas import NotificationPage, Priority, Source, UnreadCount

router = APIRouter(prefix="/api/bff/notifications", tags=["notifications"])
async def _user_with_accessible_projects(
    user: CurrentUser,
    settings: Settings,
) -> CurrentUser:
    project_ids = await list_accessible_project_ids(user, settings)

    return replace(
        user,
        project_ids=project_ids,
    )


class ListResult(BaseModel):
    """Lista de notificações com indicação de disponibilidade do upstream."""

    state: Literal["ok", "unavailable"] = "ok"
    stale: bool = False
    page: NotificationPage | None = None


class UnreadResult(BaseModel):
    state: Literal["ok", "unavailable"] = "ok"
    stale: bool = False
    count: UnreadCount | None = None


@router.get("", response_model=ListResult)
async def list_notifications(
    cursor: str | None = Query(None),
    priority: Priority | None = Query(None),
    source: Source | None = Query(None),
    status: Literal["read", "unread"] | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ListResult:
    user = await _user_with_accessible_projects(
    user,
    settings,
)
    client = get_notifications_client()
    reg = get_registry()
    try:
        result = await reg.guarded_call(
            f"notifications:list:{user.user_id}",
            lambda: client.list(
                user,
                cursor=cursor,
                priority=priority,
                source=source,
                status=status,
                limit=limit,
            ),
        )
    except UpstreamUnavailable:
        return ListResult(state="unavailable")
    return ListResult(state="ok", stale=result.stale, page=personalize_page(result.value, user))


@router.get("/unread-count", response_model=UnreadResult)
async def unread_count(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> UnreadResult:
    user = await _user_with_accessible_projects(
        user,
        settings,
    )
    client = get_notifications_client()
    reg = get_registry()
    try:
        result = await reg.guarded_call(
            f"notifications:unread:{user.user_id}",
            lambda: client.unread_count(user),
        )
    except UpstreamUnavailable:
        return UnreadResult(state="unavailable")
    return UnreadResult(state="ok", stale=result.stale, count=result.value)


@router.patch("/{notification_id}")
async def mark_read(
    notification_id: str,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    user = await _user_with_accessible_projects(
        user,
        settings,
    )

    await get_notifications_client().mark_read(
        user,
        notification_id,
    )
    get_registry().invalidate(
        f"notifications:list:{user.user_id}",
        f"notifications:unread:{user.user_id}",
    )

    return {"status": "ok"}

@router.post("/read-all")
async def mark_all_read(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    user = await _user_with_accessible_projects(
        user,
        settings,
    )

    await get_notifications_client().mark_all_read(user)
    get_registry().invalidate(
        f"notifications:list:{user.user_id}",
        f"notifications:unread:{user.user_id}",
    )

    return {"status": "ok"}
async def personalized_ws_source(events, user: CurrentUser):
    """Aplica a mesma visão por perfil a eventos recebidos em tempo real."""
    async for event in events:
        if event.get("event") == "notification.new" and isinstance(event.get("data"), dict):
            try:
                from app.domain.schemas import Notification

                notification = Notification.model_validate(event["data"])
                personalized = personalize_notification(notification, user)
                yield {**event, "data": personalized.model_dump(mode="json")}
            except (ValueError, TypeError):
                yield event
        else:
            yield event


# WebSocket fora do prefixo /api para alinhar com o proxy do Vite (/ws).
ws_router = APIRouter()

@ws_router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket) -> None:
    try:
        user = await ws_authenticate_message(websocket)

        settings = get_settings()

        user = await _user_with_accessible_projects(
            user,
            settings,
        )
    except Exception:
        await websocket.close(code=1008)
        return

    client = get_notifications_client()

    await pump(
        websocket,
        lambda: personalized_ws_source(client.ws_source(user), user),
        accept=False,
    )
