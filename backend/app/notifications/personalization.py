"""Ordenação por relevância para PO, PM e DEV, sem alterar registros do banco.

A classificação base pertence ao evento; esta pontuação é uma VISÃO por usuário.
A prioridade global continua prevalecendo (critical > high > medium > low).
"""
from __future__ import annotations

from dataclasses import replace

from app.core.security import CurrentUser, Role
from app.domain.schemas import Notification, NotificationPage, Priority, Source

_ROLE_WEIGHTS: dict[Role, dict[Source, tuple[float, str]]] = {
    Role.PO: {
        Source.BACKLOG: (0.16, "planejamento e decisões de produto"),
        Source.RELATORIOS: (0.14, "resultados do produto"),
        Source.ARTEFATOS: (0.12, "entregáveis e artefatos"),
        Source.CURADORIA: (0.04, "informações de produto"),
    },
    Role.PM: {
        Source.BACKLOG: (0.16, "andamento e impedimentos da sprint"),
        Source.RELATORIOS: (0.15, "indicadores de acompanhamento"),
        Source.GITHUB: (0.12, "andamento das entregas"),
        Source.ARTEFATOS: (0.08, "entregáveis do projeto"),
    },
    Role.DEV: {
        Source.CODE_REVIEW: (0.16, "revisões de código"),
        Source.GITHUB: (0.14, "alterações e integrações de código"),
        Source.CHAT: (0.10, "comunicação técnica"),
        Source.RAG: (0.06, "suporte técnico"),
    },
}

_ROLE_EVENT_HINTS: dict[Role, tuple[str, ...]] = {
    Role.PO: ("approval", "approved", "product", "priorit"),
    Role.PM: ("blocked", "deadline", "sprint", "overdue"),
    Role.DEV: ("review", "build", "commit", "pull_request"),
}
_PRIORITY_ORDER = {
    Priority.CRITICAL: 3,
    Priority.HIGH: 2,
    Priority.MEDIUM: 1,
    Priority.LOW: 0,
}


def personalize_notification(notification: Notification, user: CurrentUser) -> Notification:
    """Adiciona campos somente de apresentação, específicos do perfil autenticado."""
    base = notification.relevance_score
    role = user.role
    if role is None:
        return notification.model_copy(
            update={"personal_relevance_score": base, "personal_reason": None}
        )

    weight, explanation = _ROLE_WEIGHTS[role].get(
        notification.source,
        (0.0, ""),
    )
    event_type = notification.type.lower()
    context_bonus = (
        0.04
        if any(hint in event_type for hint in _ROLE_EVENT_HINTS[role])
        else 0.0
    )
    score = round(min(1.0, base + weight + context_bonus), 3)
    reason = (
        f"Para {role.value}: {explanation}."
        if weight > 0
        else (
            f"Para {role.value}: evento relacionado às suas atividades."
            if context_bonus > 0
            else None
        )
    )
    return notification.model_copy(
        update={
            "personal_relevance_score": score,
            "personal_reason": reason,
        }
    )


def notification_sort_key(notification: Notification) -> tuple[int, float, float, str]:
    """Não coloca uma notificação baixa acima de outra de prioridade crítica."""
    timestamp = notification.created_at.timestamp()
    score = (
        notification.personal_relevance_score
        if notification.personal_relevance_score is not None
        else notification.relevance_score
    )
    return (_PRIORITY_ORDER[notification.priority], score, timestamp, notification.id)


def personalize_page(page: NotificationPage, user: CurrentUser) -> NotificationPage:
    """Reordena apenas a página carregada, mantendo o cursor e o isolamento do cliente."""
    items = [personalize_notification(notification, user) for notification in page.items]
    items.sort(key=notification_sort_key, reverse=True)
    return page.model_copy(update={"items": items})


def personalize_for_project_roles(
    notification: Notification,
    user: CurrentUser,
    roles_by_project: dict[str, tuple[Role, ...] | None],
) -> Notification:
    """Calcula a melhor relevância para os papéis efetivos neste projeto.

    Papéis não confirmados mantêm o comportamento anterior. Um projeto sem
    nenhum papel reconhecido usa relevância geral, não inventa um perfil.
    Notificações globais continuam considerando o papel geral, se disponível.
    """
    if notification.project_id is None:
        return personalize_notification(notification, user)

    roles = roles_by_project.get(notification.project_id)
    if roles is None:
        return personalize_notification(notification, user)
    if not roles:
        return personalize_notification(notification, replace(user, role=None))

    candidates = [
        personalize_notification(notification, replace(user, role=role))
        for role in roles
    ]
    return max(
        candidates,
        key=lambda n: n.personal_relevance_score
        if n.personal_relevance_score is not None else n.relevance_score,
    )


def personalize_page_for_projects(
    page: NotificationPage,
    user: CurrentUser,
    roles_by_project: dict[str, tuple[Role, ...] | None],
) -> NotificationPage:
    """Aplica perfis específicos sem alterar a prioridade original do evento."""
    items = [
        personalize_for_project_roles(notification, user, roles_by_project)
        for notification in page.items
    ]
    items.sort(key=notification_sort_key, reverse=True)
    return page.model_copy(update={"items": items})
