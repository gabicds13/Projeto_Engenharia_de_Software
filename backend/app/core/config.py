"""Configuração central do BFF, carregada de variáveis de ambiente."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings do BFF do ms-dashboard.

    Todos os valores vêm de variáveis de ambiente (ou de um arquivo .env em
    desenvolvimento). Ver `.env.example` na raiz do repositório.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Aplicação
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "ms-dashboard-bff"
    port: int = 8006
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    # Mocks dos serviços downstream (demo sem os outros grupos no ar)
    use_mocks: bool = True

    # Autenticação (JWT emitido pelo Módulo 1)
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str | None = None
    jwt_audience: str | None = None

    # Login de desenvolvimento (gera tokens de PO/PM/Dev sem senha).
    # Em development fica sempre ligado. Em produção, só quando esta flag é "true"
    # — útil para demonstrar o portal enquanto o Módulo 1 (auth real) não existe.
    # DESLIGUE quando a autenticação real estiver integrada.
    enable_dev_login: bool = False

    # URLs dos serviços downstream (usadas quando use_mocks=false)
    notifications_url: str = "http://ms-notifications:8000"
    chat_url: str = "http://ms-chat:8000"
    backlog_url: str = "http://module-1:8000"  # Módulo 1 — Auth/Backlog
    github_url: str = "http://module-2:8000"  # Módulo 2 — GitHub

    # Resiliência
    upstream_timeout_seconds: float = 3.0
    circuit_breaker_fails: int = 5
    circuit_breaker_reset_seconds: float = 15.0
    cache_ttl_seconds: float = 30.0

    # Chat
    chat_history_limit: int = 50

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"

    @property
    def dev_login_enabled(self) -> bool:
        """Dev-login disponível em development ou quando habilitado explicitamente."""
        return self.is_dev or self.enable_dev_login


@lru_cache
def get_settings() -> Settings:
    return Settings()
