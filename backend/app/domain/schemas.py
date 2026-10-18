"""Schemas de domínio compartilhados (Pydantic v2)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Notificações (consumidas do ms-notifications)
# ---------------------------------------------------------------------------
class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Source(str, Enum):
    CODE_REVIEW = "code_review"
    GITHUB = "github"
    CURADORIA = "curadoria"
    ARTEFATOS = "artefatos"
    RAG = "rag"
    RELATORIOS = "relatorios"
    BACKLOG = "backlog"
    CHAT = "chat"


class Notification(BaseModel):
    id: str
    source: Source
    type: str
    priority: Priority
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str
    classified_by: Literal["llm", "rules"]
    project_id: str
    title: str
    body: str
    link: str | None = None
    created_at: datetime
    read_at: datetime | None = None


class NotificationPage(BaseModel):
    items: list[Notification]
    next_cursor: str | None = None


class UnreadCount(BaseModel):
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


# ---------------------------------------------------------------------------
# Dashboard (agregado dos Módulos 1 e 2)
# ---------------------------------------------------------------------------
class StoriesByStatus(BaseModel):
    todo: int = 0
    in_progress: int = 0
    in_review: int = 0
    done: int = 0


class WeeklyPoint(BaseModel):
    week: str  # ex.: "2026-W41"
    commits: int
    prs: int


class WeeklySeries(BaseModel):
    points: list[WeeklyPoint]


CardState = Literal["ok", "unavailable"]


class DashboardCard(BaseModel):
    key: str
    state: CardState
    stale: bool = False
    value: object | None = None


class DashboardResponse(BaseModel):
    project_id: str
    cards: list[DashboardCard]
    weekly: DashboardCard  # série do gráfico, também sujeita a indisponibilidade


# ---------------------------------------------------------------------------
# Chat (consumido do ms-chat)
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    id: str
    project_id: str
    author_id: str
    content: str
    created_at: datetime


class ChatHistory(BaseModel):
    project_id: str
    messages: list[ChatMessage]
