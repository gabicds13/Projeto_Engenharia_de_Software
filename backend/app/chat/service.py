"""Persistência e regras de acesso das conversas privadas por projeto."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.models.chat_channel import ChatChannelModel
from app.models.chat_channel_member import ChatChannelMemberModel
from app.models.chat_channel_read import ChatChannelReadModel
from app.models.chat_message import ChatMessageModel


def _direct_channel_name(user_a_id: str, user_b_id: str) -> str:
    users = sorted([user_a_id, user_b_id])
    return f"dm:{users[0]}:{users[1]}"


def get_channel_membership(
    db: Session, channel_id: str, user_id: str
) -> ChatChannelMemberModel | None:
    return db.get(ChatChannelMemberModel, (channel_id, user_id))


def is_channel_member(db: Session, channel_id: str, user_id: str) -> bool:
    """Somente convites aceitos valem como participação ativa."""
    membership = get_channel_membership(db, channel_id, user_id)
    return membership is not None and membership.accepted_at is not None


def has_pending_members(db: Session, channel_id: str) -> bool:
    count = db.scalar(
        select(func.count(ChatChannelMemberModel.user_id)).where(
            ChatChannelMemberModel.channel_id == channel_id,
            ChatChannelMemberModel.accepted_at.is_(None),
        )
    )
    return bool(count)


def _get_channel(
    db: Session, channel_id: str, project_id: str
) -> ChatChannelModel:
    channel = db.scalar(
        select(ChatChannelModel).where(
            ChatChannelModel.id == channel_id,
            ChatChannelModel.project_id == project_id,
            ChatChannelModel.type == "direct",
        )
    )
    if channel is None:
        raise NotFoundError("Conversa privada não encontrada neste projeto.")
    return channel


def _require_active_channel(
    db: Session, channel_id: str, project_id: str, user_id: str
) -> None:
    _get_channel(db, channel_id, project_id)
    if not is_channel_member(db, channel_id, user_id):
        raise ForbiddenError("Você não participa desta conversa privada.")
    if has_pending_members(db, channel_id):
        raise ForbiddenError("Aguarde o outro integrante aceitar o convite.")


def get_or_create_direct_channel(
    db: Session,
    current_user_id: str,
    target_user_id: str,
    project_id: str,
) -> ChatChannelModel:
    """Cria convite pendente; só o destinatário pode aceitar com seu login."""
    if current_user_id == target_user_id:
        raise ForbiddenError("Não é possível iniciar conversa consigo mesmo.")

    channel_name = _direct_channel_name(current_user_id, target_user_id)
    statement = select(ChatChannelModel).where(
        ChatChannelModel.project_id == project_id,
        ChatChannelModel.type == "direct",
        ChatChannelModel.name == channel_name,
    )
    existing = db.scalar(statement)
    if existing is not None:
        return existing

    now = datetime.now(UTC)
    channel = ChatChannelModel(
        id=str(uuid4()),
        project_id=project_id,
        type="direct",
        name=channel_name,
        created_at=now,
    )
    db.add(channel)
    db.flush()
    db.add_all(
        [
            ChatChannelMemberModel(
                channel_id=channel.id,
                user_id=current_user_id,
                joined_at=now,
                accepted_at=now,
            ),
            ChatChannelMemberModel(
                channel_id=channel.id,
                user_id=target_user_id,
                joined_at=now,
                accepted_at=None,
            ),
        ]
    )
    try:
        db.commit()
    except IntegrityError:
        # Dois pedidos simultâneos podem criar o mesmo canal.
        db.rollback()
        channel = db.scalar(statement)
        if channel is None:
            raise
    db.refresh(channel)
    return channel


def accept_direct_invitation(
    db: Session, channel_id: str, project_id: str, user_id: str
) -> ChatChannelModel:
    """A autenticação e a checagem de projeto ocorrem na rota antes daqui."""
    channel = _get_channel(db, channel_id, project_id)
    membership = get_channel_membership(db, channel_id, user_id)
    if membership is None:
        raise ForbiddenError("Este convite não pertence ao usuário conectado.")
    if membership.accepted_at is None:
        membership.accepted_at = datetime.now(UTC)
        db.commit()
    return channel


def list_direct_channels(
    db: Session, user_id: str, project_id: str
) -> list[tuple[ChatChannelModel, list[str]]]:
    """Inclui convites pendentes para que o destinatário possa aceitá-los."""
    channel_ids = db.scalars(
        select(ChatChannelMemberModel.channel_id).where(
            ChatChannelMemberModel.user_id == user_id
        )
    ).all()
    if not channel_ids:
        return []

    channels = db.scalars(
        select(ChatChannelModel).where(
            ChatChannelModel.id.in_(channel_ids),
            ChatChannelModel.project_id == project_id,
            ChatChannelModel.type == "direct",
        ).order_by(ChatChannelModel.created_at.desc())
    ).all()
    result = []
    for channel in channels:
        members = db.scalars(
            select(ChatChannelMemberModel.user_id).where(
                ChatChannelMemberModel.channel_id == channel.id
            )
        ).all()
        result.append((channel, list(members)))
    return result


def get_direct_messages(
    db: Session,
    channel_id: str,
    project_id: str,
    user_id: str,
    limit: int = 50,
) -> list[ChatMessageModel]:
    _require_active_channel(db, channel_id, project_id, user_id)
    rows = db.scalars(
        select(ChatMessageModel).where(
            ChatMessageModel.channel_id == channel_id,
            ChatMessageModel.project_id == project_id,
        ).order_by(ChatMessageModel.created_at.desc()).limit(limit)
    ).all()
    return list(reversed(rows))


def send_direct_message(
    db: Session,
    channel_id: str,
    project_id: str,
    user_id: str,
    content: str,
) -> ChatMessageModel:
    _require_active_channel(db, channel_id, project_id, user_id)
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
    db: Session, channel_id: str, user_id: str, project_id: str
) -> int:
    _require_active_channel(db, channel_id, project_id, user_id)
    read_state = db.get(ChatChannelReadModel, (channel_id, user_id))
    query = select(func.count(ChatMessageModel.id)).where(
        ChatMessageModel.channel_id == channel_id,
        ChatMessageModel.author_id != user_id,
    )
    if read_state is not None:
        query = query.where(ChatMessageModel.created_at > read_state.last_read_at)
    return int(db.scalar(query) or 0)


def mark_channel_as_read(
    db: Session, channel_id: str, user_id: str, project_id: str
) -> None:
    _require_active_channel(db, channel_id, project_id, user_id)
    now = datetime.now(UTC)
    read_state = db.get(ChatChannelReadModel, (channel_id, user_id))
    if read_state is None:
        db.add(
            ChatChannelReadModel(
                channel_id=channel_id, user_id=user_id, last_read_at=now
            )
        )
    else:
        read_state.last_read_at = now
    db.commit()
