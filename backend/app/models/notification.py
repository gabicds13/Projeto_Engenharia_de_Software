from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotificationModel(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str | None] = mapped_column(
    String(100),
    unique=True,
    nullable=True,
    index=True,
    )

    project_id: Mapped[str] = mapped_column(String(100), index=True)

    source: Mapped[str] = mapped_column(String(50), index=True)

    type: Mapped[str] = mapped_column(String(100))

    priority: Mapped[str] = mapped_column(String(20), index=True)

    relevance_score: Mapped[float] = mapped_column(Float)

    reason: Mapped[str] = mapped_column(Text)

    classified_by: Mapped[str] = mapped_column(String(20))

    title: Mapped[str] = mapped_column(String(255))

    body: Mapped[str] = mapped_column(Text)

    link: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )