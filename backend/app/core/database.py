from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    settings = get_settings()

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL não configurada.")

    database_url = settings.database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

    return create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args={
        "connect_timeout": 10,
    },
)


@lru_cache
def get_session_factory():
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


def get_db():
    db: Session = get_session_factory()()

    try:
        yield db
    finally:
        db.close()