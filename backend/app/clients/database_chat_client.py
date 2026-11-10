from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import get_session_factory
from app.core.security import CurrentUser
from app.domain.schemas import ChatMessage
from app.models.chat_channel import ChatChannelModel
from app.models.chat_message import ChatMessageModel


def _to_chat_message(row: ChatMessageModel) -> ChatMessage:
    return ChatMessage(
        id=row.id,
        project_id=row.project_id,
        author_id=row.author_id,
        content=row.content,
        created_at=row.created_at,
    )


def _get_or_create_project_channel(
    db,
    project_id: str,
) -> ChatChannelModel:
    channel = db.scalar(
        select(ChatChannelModel).where(
            ChatChannelModel.project_id == project_id,
            ChatChannelModel.type == "project",
            ChatChannelModel.name == "Geral",
        )
    )

    if channel is not None:
        return channel

    channel = ChatChannelModel(
        id=str(uuid4()),
        project_id=project_id,
        type="project",
        name="Geral",
        created_at=datetime.now(timezone.utc),
    )

    db.add(channel)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        channel = db.scalar(
            select(ChatChannelModel).where(
                ChatChannelModel.project_id == project_id,
                ChatChannelModel.type == "project",
                ChatChannelModel.name == "Geral",
            )
        )

        if channel is None:
            raise

    return channel


class DatabaseChatClient:
    async def history(
        self,
        user: CurrentUser,
        project_id: str,
        *,
        limit: int = 50,
    ) -> list[ChatMessage]:
        session_factory = get_session_factory()

        with session_factory() as db:
            channel = _get_or_create_project_channel(
                db,
                project_id,
            )

            rows = db.scalars(
                select(ChatMessageModel)
                .where(
                    ChatMessageModel.channel_id == channel.id,
                )
                .order_by(ChatMessageModel.created_at.desc())
                .limit(limit)
            ).all()

        rows.reverse()

        return [
            _to_chat_message(row)
            for row in rows
        ]

    async def post(
        self,
        user: CurrentUser,
        project_id: str,
        text: str,
    ) -> ChatMessage:
        session_factory = get_session_factory()

        with session_factory() as db:
            channel = _get_or_create_project_channel(
                db,
                project_id,
            )

            row = ChatMessageModel(
                id=str(uuid4()),
                channel_id=channel.id,
                project_id=project_id,
                author_id=user.user_id,
                content=text,
                created_at=datetime.now(timezone.utc),
            )

            db.add(row)
            db.commit()

        return _to_chat_message(row)

    async def ws_source(
        self,
        user: CurrentUser,
        project_id: str,
    ) -> AsyncIterator[dict]:
        last_check = datetime.now(timezone.utc)
        session_factory = get_session_factory()

        while True:
            await asyncio.sleep(2)

            with session_factory() as db:
                channel = _get_or_create_project_channel(
                    db,
                    project_id,
                )

                rows = db.scalars(
                    select(ChatMessageModel)
                    .where(
                        ChatMessageModel.channel_id == channel.id,
                        ChatMessageModel.created_at > last_check,
                    )
                    .order_by(ChatMessageModel.created_at.asc())
                ).all()

            if rows:
                last_check = max(
                    row.created_at
                    for row in rows
                )

            for row in rows:
                message = _to_chat_message(row)

                yield {
                    "event": "chat.message",
                    "data": message.model_dump(mode="json"),
                }