"""Rotas de chat: histórico + envio (REST) e WebSocket bridge para o ms-chat.

O acesso é restrito aos projetos presentes no token do usuário (Requisito 5.1).
"""
from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Response, WebSocket
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.chat.mentions import extract_mentions
from app.chat.realtime import direct_chat_hub
from app.chat.service import (
    accept_direct_invitation,
    get_channel_membership,
    has_pending_members,
    get_channel_unread_count,
    get_direct_messages,
    get_or_create_direct_channel,
    is_channel_member,
    list_direct_channels,
    mark_channel_as_read,
    send_direct_message,
)
from app.clients import get_chat_client, get_notifications_client
from app.clients.projects_client import ensure_project_access
from app.core.config import get_settings
from app.core.database import get_db, get_session_factory
from app.core.resilience import UpstreamUnavailable, get_registry
from app.core.security import (
    CurrentUser,
    get_current_user,
    ws_authenticate_message,
)
from app.core.ws_bridge import pump
from app.domain.schemas import (
    ChatMessage,
    Notification,
    NotificationScope,
    Priority,
    Source,
)

router = APIRouter(prefix="/api/bff/chat", tags=["chat"])
logger = logging.getLogger(__name__)


class HistoryResult(BaseModel):
    state: Literal["ok", "unavailable"] = "ok"
    stale: bool = False
    project_id: str
    messages: list[ChatMessage] = Field(default_factory=list)


class PostMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
class DirectMessageIn(BaseModel):
    target_user_id: str = Field(min_length=1, max_length=100)


class DirectChannelOut(BaseModel):
    id: str
    project_id: str
    type: str
    name: str

class DirectChannelListItem(BaseModel):
    id: str
    project_id: str
    type: str
    member_ids: list[str]
    created_at: datetime
    pending: bool = False
    needs_my_acceptance: bool = False

class DirectChatMessageOut(BaseModel):
    id: str
    channel_id: str
    project_id: str
    author_id: str
    content: str
    created_at: datetime

class UnreadResult(BaseModel):
    project_id: str
    unread: int

class ChannelUnreadOut(BaseModel):
    channel_id: str
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

    message = await get_chat_client().post(
        user,
        project_id,
        payload.content,
    )

    mentions = extract_mentions(
        payload.content,
        user.user_id,
    )

    # A mensagem já foi persistida. A notificação de menção é um efeito
    # secundário: falhas nesse serviço não devem transformar o envio em erro.
    if mentions:
        try:
            notifications = get_notifications_client()
        except Exception as exc:
            logger.warning(
                "Notificações indisponíveis após envio do chat (%s).",
                type(exc).__name__,
            )
        else:
            for target_user_id in mentions:
                try:
                    await notifications.publish(
                        Notification(
                            id=str(uuid4()),
                            event_id=f"chat-mention-{message.id}-{target_user_id}"[:100],
                            source=Source.CHAT,
                            type="chat.mention",
                            priority=Priority.MEDIUM,
                            relevance_score=0.7,
                            reason="Você foi mencionado em uma mensagem do Chat.",
                            classified_by="rules",
                            scope=NotificationScope.PROJECT,
                            project_id=project_id,
                            target_user_id=target_user_id,
                            title="Você foi mencionado no Chat",
                            body=f"{user.user_id}: {payload.content}",
                            link="/chat",
                            created_at=message.created_at.astimezone(UTC),
                            read_at=None,
                        )
                    )
                except Exception as exc:
                    # Não registrar o corpo da mensagem nem IDs pessoais no log.
                    logger.warning(
                        "Não foi possível gerar uma notificação de menção (%s).",
                        type(exc).__name__,
                    )

    return message 


ws_router = APIRouter()

@router.post(
    "/rooms/{project_id}/direct",
    response_model=DirectChannelOut,
)
async def create_direct_channel(
    project_id: str,
    payload: DirectMessageIn,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DirectChannelOut:
    await _require_project(user, project_id)

    channel = get_or_create_direct_channel(
        db=db,
        current_user_id=user.user_id,
        target_user_id=payload.target_user_id,
        project_id=project_id,
    )

    return DirectChannelOut(
        id=channel.id,
        project_id=channel.project_id,
        type=channel.type,
        name=channel.name,
    )

@router.post(
    "/rooms/{project_id}/direct/{channel_id}/accept",
    response_model=DirectChannelOut,
)
async def accept_direct_channel(
    project_id: str,
    channel_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DirectChannelOut:
    # A pessoa convidada confirma o acesso ao projeto com seu próprio JWT.
    await _require_project(user, project_id)
    channel = accept_direct_invitation(
        db=db,
        channel_id=channel_id,
        project_id=project_id,
        user_id=user.user_id,
    )
    return DirectChannelOut(
        id=channel.id,
        project_id=channel.project_id,
        type=channel.type,
        name=channel.name,
    )


@router.get(
    "/rooms/{project_id}/direct",
    response_model=list[DirectChannelListItem],
)
async def get_direct_channels(
    project_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DirectChannelListItem]:
    await _require_project(user, project_id)

    channels = list_direct_channels(
        db=db,
        user_id=user.user_id,
        project_id=project_id,
    )

    return [
        DirectChannelListItem(
            id=channel.id,
            project_id=channel.project_id,
            type=channel.type,
            member_ids=members,
            created_at=channel.created_at,
            pending=has_pending_members(db, channel.id),
            needs_my_acceptance=(
                (membership := get_channel_membership(db, channel.id, user.user_id))
                is not None and membership.accepted_at is None
            ),
        )
        for channel, members in channels
    ]

@router.get(
    "/rooms/{project_id}/direct/{channel_id}/messages",
    response_model=list[DirectChatMessageOut],
)
async def direct_history(
    project_id: str,
    channel_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DirectChatMessageOut]:
    await _require_project(user, project_id)

    messages = get_direct_messages(
        db=db,
        channel_id=channel_id,
        project_id=project_id,
        user_id=user.user_id,
    )

    return [
        DirectChatMessageOut(
            id=message.id,
            channel_id=message.channel_id,
            project_id=message.project_id,
            author_id=message.author_id,
            content=message.content,
            created_at=message.created_at,
        )
        for message in messages
    ]


@router.post(
    "/rooms/{project_id}/direct/{channel_id}/messages",
    response_model=DirectChatMessageOut,
)
async def post_direct_message(
    project_id: str,
    channel_id: str,
    payload: PostMessageIn,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DirectChatMessageOut:
    await _require_project(user, project_id)

    message = send_direct_message(
        db=db,
        channel_id=channel_id,
        project_id=project_id,
        user_id=user.user_id,
        content=payload.content,
    )
    await direct_chat_hub.publish(
    channel_id,
    {
        "event": "chat.direct.message",
        "data": {
            "id": message.id,
            "channel_id": message.channel_id,
            "project_id": message.project_id,
            "author_id": message.author_id,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        },
    },
)

    return DirectChatMessageOut(
        id=message.id,
        channel_id=message.channel_id,
        project_id=message.project_id,
        author_id=message.author_id,
        content=message.content,
        created_at=message.created_at,
    )

@router.get(
    "/rooms/{project_id}/direct/{channel_id}/unread",
    response_model=ChannelUnreadOut,
)
async def direct_unread_count(
    project_id: str,
    channel_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChannelUnreadOut:
    await _require_project(user, project_id)

    unread = get_channel_unread_count(
        db=db,
        channel_id=channel_id,
        user_id=user.user_id,
        project_id=project_id,
    )

    return ChannelUnreadOut(
        channel_id=channel_id,
        unread=unread,
    )


@router.post(
    "/rooms/{project_id}/direct/{channel_id}/read",
    status_code=204,
)
async def mark_direct_read(
    project_id: str,
    channel_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    await _require_project(user, project_id)

    mark_channel_as_read(
        db=db,
        channel_id=channel_id,
        user_id=user.user_id,
        project_id=project_id,
    )

    return Response(status_code=204)

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

@ws_router.websocket("/ws/chat/direct")
async def direct_chat_ws(
    websocket: WebSocket,
) -> None:
    try:
        user = await ws_authenticate_message(websocket)

        project_id = websocket.query_params.get("project_id")
        channel_id = websocket.query_params.get("channel_id")

        if not project_id or not channel_id:
            await websocket.close(code=1008)
            return

        await _require_project(
            user,
            project_id,
        )

        session_factory = get_session_factory()

        with session_factory() as db:
            member = is_channel_member(
                db,
                channel_id,
                user.user_id,
            )
            from app.chat.service import _get_channel
            _get_channel(db, channel_id, project_id)
            pending = has_pending_members(db, channel_id)

        if not member or pending:
            await websocket.close(code=1008)
            return

    except Exception:
        await websocket.close(code=1008)
        return

    await pump(
        websocket,
        lambda: direct_chat_hub.subscribe(channel_id),
        accept=False,
    )
