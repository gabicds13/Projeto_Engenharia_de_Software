"""Rotas de chat: histórico + envio (REST) e WebSocket bridge para o ms-chat.

O acesso é restrito aos projetos presentes no token do usuário (Requisito 5.1).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Response, WebSocket
from pydantic import BaseModel, Field

from app.clients import get_chat_client
from app.core.config import get_settings

from app.core.resilience import UpstreamUnavailable, get_registry
from app.core.security import (
    CurrentUser,
    get_current_user,
    ws_authenticate_message,
)
from app.core.ws_bridge import pump
from app.domain.schemas import ChatMessage
from app.clients.projects_client import ensure_project_access

router = APIRouter(prefix="/api/bff/chat", tags=["chat"])


class HistoryResult(BaseModel):
    state: Literal["ok", "unavailable"] = "ok"
    stale: bool = False
    project_id: str
    messages: list[ChatMessage] = Field(default_factory=list)


class PostMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

class UnreadResult(BaseModel):
    project_id: str
    unread: int

async def _require_project(
    user: CurrentUser,
    project_id: str,
) -> None:
    await ensure_project_access(
        project_id,
        user,
        get_settings(),
    )


@router.get("/rooms/{project_id}/messages", response_model=HistoryResult)
async def history(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> HistoryResult:
    await _require_project(user, project_id)
    client = get_chat_client()
    reg = get_registry()
    limit = get_settings().chat_history_limit
    try:
        result = await reg.guarded_call(
            f"chat:history:{project_id}",
            lambda: client.history(user, project_id, limit=limit),
        )
    except UpstreamUnavailable:
        return HistoryResult(state="unavailable", project_id=project_id)
    return HistoryResult(
        state="ok", stale=result.stale, project_id=project_id, messages=result.value
    )

@router.get(
    "/rooms/{project_id}/unread",
    response_model=UnreadResult,
)
async def unread_count(
    project_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> UnreadResult:
    await _require_project(user, project_id)

    unread = await get_chat_client().unread_count(
        user,
        project_id,
    )

    return UnreadResult(
        project_id=project_id,
        unread=unread,
    )
@router.post(
    "/rooms/{project_id}/read",
    status_code=204,
)
async def mark_read(
    project_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    await _require_project(user, project_id)

    await get_chat_client().mark_read(
        user,
        project_id,
    )

    return Response(status_code=204)

@router.post("/rooms/{project_id}/messages", response_model=ChatMessage)
async def post_message(
    project_id: str,
    payload: PostMessageIn,
    user: CurrentUser = Depends(get_current_user),
) -> ChatMessage:
    await _require_project(user, project_id)
    return await get_chat_client().post(user, project_id, payload.content)


ws_router = APIRouter()


@ws_router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket) -> None:
    try:
        user = await ws_authenticate_message(websocket)

        project_id = websocket.query_params.get("project_id")

        if not project_id:
            await websocket.close(code=1008)
            return

        await _require_project(
            user,
            project_id,
        )
    except Exception:
        await websocket.close(code=1008)
        return

    client = get_chat_client()

    await pump(
        websocket,
        lambda: client.ws_source(user, project_id),
        accept=False,
    )
