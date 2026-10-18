"""Fábrica de clients upstream, selecionados por USE_MOCKS.

Os mocks são singletons por processo (mantêm estado de demo em memória: histórico
de chat, notificações marcadas como lidas etc.).
"""
from __future__ import annotations

from functools import lru_cache

from app.clients.backlog_client import BacklogClient, HttpBacklogClient, MockBacklogClient
from app.clients.chat_client import ChatClient, HttpChatClient, MockChatClient
from app.clients.github_client import GithubClient, HttpGithubClient, MockGithubClient
from app.clients.notifications_client import (
    HttpNotificationsClient,
    MockNotificationsClient,
    NotificationsClient,
)
from app.core.config import get_settings


@lru_cache
def get_backlog_client() -> BacklogClient:
    s = get_settings()
    return MockBacklogClient() if s.use_mocks else HttpBacklogClient(s.backlog_url)


@lru_cache
def get_github_client() -> GithubClient:
    s = get_settings()
    return MockGithubClient() if s.use_mocks else HttpGithubClient(s.github_url)


@lru_cache
def get_notifications_client() -> NotificationsClient:
    s = get_settings()
    return MockNotificationsClient() if s.use_mocks else HttpNotificationsClient(s.notifications_url)


@lru_cache
def get_chat_client() -> ChatClient:
    s = get_settings()
    return MockChatClient() if s.use_mocks else HttpChatClient(s.chat_url)
