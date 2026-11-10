from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotificationReadModel(Base):
    __tablename__ = "notification_reads"

    notification_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "notifications.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )