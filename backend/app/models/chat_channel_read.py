from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChatChannelReadModel(Base):
    __tablename__ = "chat_channel_reads"

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

    last_read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )