from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChatChannelModel(Base):
    __tablename__ = "chat_channels"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    project_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="project",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Geral",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "type",
            "name",
            name="uq_chat_channel_project_type_name",
        ),
    )