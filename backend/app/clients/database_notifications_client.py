from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator

from sqlalchemy import select, update

from app.core.database import get_session_factory
from app.core.security import CurrentUser
from app.domain.schemas import (
    Notification,
    NotificationPage,
    Priority,
    Source,
    UnreadCount,
)
from app.models.notification import NotificationModel


def _to_notification(row: NotificationModel) -> Notification:
    return Notification(
        id=row.id,
        project_id=row.project_id,
        source=Source(row.source),
        type=row.type,
        priority=Priority(row.priority),
        relevance_score=row.relevance_score,
        reason=row.reason,
        classified_by=row.classified_by,
        title=row.title,
        body=row.body,
        link=row.link,
        created_at=row.created_at,
        read_at=row.read_at,
    )


class DatabaseNotificationsClient:
    async def publish(
        self,
        notification: Notification,
    ) -> Notification:
        session_factory = get_session_factory()

        with session_factory() as db:
            row = NotificationModel(
                id=notification.id,
                project_id=notification.project_id,
                source=notification.source.value,
                type=notification.type,
                priority=notification.priority.value,
                relevance_score=notification.relevance_score,
                reason=notification.reason,
                classified_by=notification.classified_by,
                title=notification.title,
                body=notification.body,
                link=notification.link,
                created_at=notification.created_at,
                read_at=notification.read_at,
            )

            db.add(row)
            db.commit()

        return notification

    async def list(
        self,
        user: CurrentUser,
        *,
        cursor: str | None = None,
        priority: Priority | None = None,
        source: Source | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> NotificationPage:
        session_factory = get_session_factory()

        with session_factory() as db:
            statement = select(NotificationModel)

            if priority is not None:
                statement = statement.where(
                    NotificationModel.priority == priority.value
                )

            if source is not None:
                statement = statement.where(
                    NotificationModel.source == source.value
                )

            if status == "unread":
                statement = statement.where(
                    NotificationModel.read_at.is_(None)
                )

            elif status == "read":
                statement = statement.where(
                    NotificationModel.read_at.is_not(None)
                )

            statement = (
                statement
                .order_by(NotificationModel.created_at.desc())
                .limit(limit)
            )

            rows = db.scalars(statement).all()

        return NotificationPage(
            items=[_to_notification(row) for row in rows],
            next_cursor=None,
        )

    async def unread_count(
        self,
        user: CurrentUser,
    ) -> UnreadCount:
        session_factory = get_session_factory()

        with session_factory() as db:
            rows = db.scalars(
                select(NotificationModel).where(
                    NotificationModel.read_at.is_(None)
                )
            ).all()

        result = UnreadCount(total=len(rows))

        for row in rows:
            priority = Priority(row.priority)
            setattr(
                result,
                priority.value,
                getattr(result, priority.value) + 1,
            )

        return result

    async def mark_read(
        self,
        user: CurrentUser,
        notif_id: str,
    ) -> None:
        session_factory = get_session_factory()

        with session_factory() as db:
            row = db.get(NotificationModel, notif_id)

            if row is not None and row.read_at is None:
                row.read_at = datetime.now(timezone.utc)
                db.commit()

    async def mark_all_read(
        self,
        user: CurrentUser,
    ) -> None:
        session_factory = get_session_factory()

        with session_factory() as db:
            db.execute(
                update(NotificationModel)
                .where(NotificationModel.read_at.is_(None))
                .values(read_at=datetime.now(timezone.utc))
            )
            db.commit()

    async def ws_source(
        self,
        user: CurrentUser,
    ) -> AsyncIterator[dict]:
        last_check = datetime.now(timezone.utc)
        session_factory = get_session_factory()

        while True:
            await asyncio.sleep(2)

            with session_factory() as db:
                rows = db.scalars(
                    select(NotificationModel)
                    .where(NotificationModel.created_at > last_check)
                    .order_by(NotificationModel.created_at.asc())
                ).all()

            if rows:
                last_check = max(row.created_at for row in rows)

            for row in rows:
                notification = _to_notification(row)

                yield {
                    "event": "notification.new",
                    "data": notification.model_dump(mode="json"),
                }