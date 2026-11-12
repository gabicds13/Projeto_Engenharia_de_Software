from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChatChannelMemberModel(Base):
    __tablename__ = "chat_channel_members"

    channel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "chat_channels.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Convite pendente ate o destinatario confirmar com seu proprio login.
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
