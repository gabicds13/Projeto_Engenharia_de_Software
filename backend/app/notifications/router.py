"""Rotas de notificações: proxy REST + WebSocket bridge para o ms-notifications."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, WebSocket
from pydantic import BaseModel

from app.clients import get_notifications_client
from app.core.resilience import UpstreamUnavailable, get_registry
from app.core.security import CurrentUser, get_current_user, ws_authenticate
from app.core.ws_bridge import pump
from app.domain.schemas import NotificationPage, Priority, Source, UnreadCount

router = APIRouter(prefix="/api/bff/notifications", tags=["notifications"])


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
) -> ListResult:
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
    return ListResult(state="ok", stale=result.stale, page=result.value)


@router.get("/unread-count", response_model=UnreadResult)
async def unread_count(user: CurrentUser = Depends(get_current_user)) -> UnreadResult:
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
    notification_id: str, user: CurrentUser = Depends(get_current_user)
) -> dict[str, str]:
    await get_notifications_client().mark_read(user, notification_id)
    return {"status": "ok"}


@router.post("/read-all")
async def mark_all_read(user: CurrentUser = Depends(get_current_user)) -> dict[str, str]:
    await get_notifications_client().mark_all_read(user)
    return {"status": "ok"}


# WebSocket fora do prefixo /api para alinhar com o proxy do Vite (/ws).
ws_router = APIRouter()


@ws_router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket) -> None:
    try:
        user = await ws_authenticate(websocket)
    except Exception:
        await websocket.close(code=1008)  # policy violation
        return
    client = get_notifications_client()
    await pump(websocket, lambda: client.ws_source(user))
