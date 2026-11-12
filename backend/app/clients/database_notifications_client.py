from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError

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
from app.models.notification_read import NotificationReadModel


def _to_notification(
    row: NotificationModel,
    read_at: datetime | None = None,
) -> Notification:
    return Notification(
        id=row.id,
        event_id=row.event_id,
        scope=row.scope,
        project_id=row.project_id,
        target_user_id=row.target_user_id,
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
        read_at=read_at,
    )
def _visibility_filter(user: CurrentUser):
    return and_(
        or_(
            NotificationModel.scope == "global",
            NotificationModel.project_id.in_(user.project_ids),
        ),
        or_(
            NotificationModel.target_user_id.is_(None),
            NotificationModel.target_user_id == user.user_id,
        ),
    )
class DatabaseNotificationsClient:
    async def publish(
        self,
        notification: Notification,
    ) -> Notification:
        session_factory = get_session_factory()

        with session_factory() as db:
            if notification.event_id:
                existing = db.scalar(
                    select(NotificationModel).where(
                        NotificationModel.event_id == notification.event_id
                    )
                )

                if existing is not None:
                    return _to_notification(existing)

            row = NotificationModel(
                id=notification.id,
                event_id=notification.event_id,
                scope=notification.scope.value,
                project_id=notification.project_id,
                target_user_id=notification.target_user_id,
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

            try:
                db.commit()
            except IntegrityError:
                db.rollback()

                if notification.event_id:
                    existing = db.scalar(
                        select(NotificationModel).where(
                            NotificationModel.event_id == notification.event_id
                        )
                    )

                    if existing is not None:
                        return _to_notification(existing)

                raise

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
            statement = (
                select(
                    NotificationModel,
                    NotificationReadModel.read_at,
                )
                .outerjoin(
                    NotificationReadModel,
                    (
                        NotificationReadModel.notification_id
                        == NotificationModel.id
                    )
                    & (
                        NotificationReadModel.user_id
                        == user.user_id
                    ),
                )
                .where(
                    _visibility_filter(user)
                )
            )

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
                    NotificationReadModel.read_at.is_(None)
                )
            elif status == "read":
                statement = statement.where(
                    NotificationReadModel.read_at.is_not(None)
                )

            statement = (
                statement
                .order_by(NotificationModel.created_at.desc())
                .limit(limit)
            )

            rows = db.execute(statement).all()

        return NotificationPage(
            items=[
                _to_notification(row, read_at)
                for row, read_at in rows
            ],
            next_cursor=None,
        )

    async def unread_count(
        self,
        user: CurrentUser,
    ) -> UnreadCount:
        session_factory = get_session_factory()

        with session_factory() as db:
            rows = db.execute(
                select(
                    NotificationModel,
                    NotificationReadModel.read_at,
                )
                .outerjoin(
                    NotificationReadModel,
                    (
                        NotificationReadModel.notification_id
                        == NotificationModel.id
                    )
                    & (
                        NotificationReadModel.user_id
                        == user.user_id
                    ),
                )
                .where(
                    _visibility_filter(user),
                    NotificationReadModel.read_at.is_(None),
                )
            ).all()

        result = UnreadCount(total=len(rows))

        for row, _read_at in rows:
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
            notification = db.scalar(
                select(NotificationModel).where(
                    NotificationModel.id == notif_id,
                    _visibility_filter(user),
                )
            )

            if notification is None:
                return

            existing_read = db.get(
                NotificationReadModel,
                (notif_id, user.user_id),
            )

            if existing_read is not None:
                return

            db.add(
                NotificationReadModel(
                    notification_id=notif_id,
                    user_id=user.user_id,
                    read_at=datetime.now(UTC),
                )
            )

            db.commit()
    async def mark_all_read(
        self,
        user: CurrentUser,
    ) -> None:
        session_factory = get_session_factory()

        with session_factory() as db:
            notification_ids = db.scalars(
             select(NotificationModel.id).where(
                _visibility_filter(user)
             )
            ).all()

            if not notification_ids:
                return

            existing_reads = set(
                db.scalars(
                    select(NotificationReadModel.notification_id).where(
                        NotificationReadModel.user_id == user.user_id,
                        NotificationReadModel.notification_id.in_(
                            notification_ids
                        ),
                    )
                ).all()
            )

            read_at = datetime.now(UTC)

            for notification_id in notification_ids:
                if notification_id in existing_reads:
                    continue

                db.add(
                    NotificationReadModel(
                        notification_id=notification_id,
                        user_id=user.user_id,
                        read_at=read_at,
                    )
                )

            db.commit()

    async def ws_source(
        self,
        user: CurrentUser,
    ) -> AsyncIterator[dict]:
        # Nao bloqueia o event loop enquanto o Neon responde.
        last_check = datetime.now(UTC)

        def fetch_newer(since: datetime) -> list[Notification]:
            session_factory = get_session_factory()
            with session_factory() as db:
                rows = db.scalars(
                    select(NotificationModel)
                    .where(
                        _visibility_filter(user),
                        NotificationModel.created_at > since,
                    )
                    .order_by(NotificationModel.created_at.asc())
                ).all()
                return [_to_notification(row) for row in rows]

        while True:
            await asyncio.sleep(2)
            notifications = await asyncio.to_thread(fetch_newer, last_check)

            if notifications:
                last_check = max(n.created_at for n in notifications)
            for notification in notifications:
                yield {
                    "event": "notification.new",
                    "data": notification.model_dump(mode="json"),
                }
