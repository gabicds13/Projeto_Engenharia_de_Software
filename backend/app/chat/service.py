from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.chat_channel import ChatChannelModel
from app.models.chat_channel_member import ChatChannelMemberModel
from app.models.chat_channel_read import ChatChannelReadModel
from app.models.chat_message import ChatMessageModel


def _direct_channel_name(
    user_a_id: str,
    user_b_id: str,
) -> str:
    users = sorted([user_a_id, user_b_id])
    return f"dm:{users[0]}:{users[1]}"


def get_or_create_direct_channel(
    db: Session,
    current_user_id: str,
    target_user_id: str,
    project_id: str,
) -> ChatChannelModel:
    if current_user_id == target_user_id:
        raise ValueError(
            "Não é possível criar uma conversa direta consigo mesmo."
        )

    channel_name = _direct_channel_name(
        current_user_id,
        target_user_id,
    )

    channel = db.execute(
        select(ChatChannelModel).where(
            ChatChannelModel.project_id == project_id,
            ChatChannelModel.type == "direct",
            ChatChannelModel.name == channel_name,
        )
    ).scalar_one_or_none()

    if channel is not None:
        return channel

    channel = ChatChannelModel(
        id=str(uuid4()),
        project_id=project_id,
        type="direct",
        name=channel_name,
        created_at=datetime.now(UTC),
    )

    db.add(channel)
    db.flush()

    joined_at = datetime.now(UTC)

    db.add_all(
        [
            ChatChannelMemberModel(
                channel_id=channel.id,
                user_id=current_user_id,
                joined_at=joined_at,
            ),
            ChatChannelMemberModel(
                channel_id=channel.id,
                user_id=target_user_id,
                joined_at=joined_at,
            ),
        ]
    )

    db.commit()
    db.refresh(channel)

    return channel

def list_direct_channels(
    db: Session,
    user_id: str,
    project_id: str,
) -> list[tuple[ChatChannelModel, list[str]]]:
    """
    Lista as conversas diretas do usuário dentro de um projeto.
    Retorna o canal e os IDs dos participantes.
    """

    channel_ids = db.execute(
        select(ChatChannelMemberModel.channel_id).where(
            ChatChannelMemberModel.user_id == user_id
        )
    ).scalars().all()

    if not channel_ids:
        return []

    channels = db.execute(
        select(ChatChannelModel)
        .where(
            ChatChannelModel.id.in_(channel_ids),
            ChatChannelModel.project_id == project_id,
            ChatChannelModel.type == "direct",
        )
        .order_by(ChatChannelModel.created_at.desc())
    ).scalars().all()

    result: list[tuple[ChatChannelModel, list[str]]] = []

    for channel in channels:
        members = db.execute(
            select(ChatChannelMemberModel.user_id).where(
                ChatChannelMemberModel.channel_id == channel.id
            )
        ).scalars().all()

        result.append(
            (
                channel,
                list(members),
            )
        )

    return result

def is_channel_member(
    db: Session,
    channel_id: str,
    user_id: str,
) -> bool:
    member = db.execute(
        select(ChatChannelMemberModel).where(
            ChatChannelMemberModel.channel_id == channel_id,
            ChatChannelMemberModel.user_id == user_id,
        )
    ).scalar_one_or_none()

    return member is not None


def get_direct_messages(
    db: Session,
    channel_id: str,
    project_id: str,
    user_id: str,
    limit: int = 50,
) -> list[ChatMessageModel]:
    channel = db.execute(
        select(ChatChannelModel).where(
            ChatChannelModel.id == channel_id,
            ChatChannelModel.project_id == project_id,
            ChatChannelModel.type == "direct",
        )
    ).scalar_one_or_none()

    if channel is None:
        raise ValueError("Canal direto não encontrado.")

    if not is_channel_member(
        db,
        channel_id,
        user_id,
    ):
        raise PermissionError(
            "Usuário não participa desta conversa."
        )

    messages = db.execute(
        select(ChatMessageModel)
        .where(
            ChatMessageModel.channel_id == channel_id,
            ChatMessageModel.project_id == project_id,
        )
        .order_by(ChatMessageModel.created_at.desc())
        .limit(limit)
    ).scalars().all()

    return list(reversed(messages))


def send_direct_message(
    db: Session,
    channel_id: str,
    project_id: str,
    user_id: str,
    content: str,
) -> ChatMessageModel:
    channel = db.execute(
        select(ChatChannelModel).where(
            ChatChannelModel.id == channel_id,
            ChatChannelModel.project_id == project_id,
            ChatChannelModel.type == "direct",
        )
    ).scalar_one_or_none()

    if channel is None:
        raise ValueError("Canal direto não encontrado.")

    if not is_channel_member(
        db,
        channel_id,
        user_id,
    ):
        raise PermissionError(
            "Usuário não participa desta conversa."
        )

    message = ChatMessageModel(
        id=str(uuid4()),
        channel_id=channel_id,
        project_id=project_id,
        author_id=user_id,
        content=content,
        created_at=datetime.now(UTC),
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message

def get_channel_unread_count(
    db: Session,
    channel_id: str,
    user_id: str,
) -> int:
    if not is_channel_member(
        db,
        channel_id,
        user_id,
    ):
        raise PermissionError(
            "Usuário não participa deste canal."
        )

    read_state = db.execute(
        select(ChatChannelReadModel).where(
            ChatChannelReadModel.channel_id == channel_id,
            ChatChannelReadModel.user_id == user_id,
        )
    ).scalar_one_or_none()

    query = select(func.count(ChatMessageModel.id)).where(
        ChatMessageModel.channel_id == channel_id,
        ChatMessageModel.author_id != user_id,
    )

    if read_state is not None:
        query = query.where(
            ChatMessageModel.created_at > read_state.last_read_at
        )

    return int(db.execute(query).scalar_one())

def mark_channel_as_read(
    db: Session,
    channel_id: str,
    user_id: str,
) -> None:
    if not is_channel_member(
        db,
        channel_id,
        user_id,
    ):
        raise PermissionError(
            "Usuário não participa deste canal."
        )

    now = datetime.now(UTC)

    read_state = db.execute(
        select(ChatChannelReadModel).where(
            ChatChannelReadModel.channel_id == channel_id,
            ChatChannelReadModel.user_id == user_id,
        )
    ).scalar_one_or_none()

    if read_state is None:
        read_state = ChatChannelReadModel(
            channel_id=channel_id,
            user_id=user_id,
            last_read_at=now,
        )

        db.add(read_state)

    else:
        read_state.last_read_at = now

    db.commit()