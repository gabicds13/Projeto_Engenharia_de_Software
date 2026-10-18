"""Ponto de entrada do BFF do ms-dashboard."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.health import router as health_router
from app.core.logging import CorrelationIdMiddleware, configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="ms-dashboard BFF",
        description=(
            "Backend for Frontend do portal do Módulo 6. Agrega métricas e "
            "encapsula os serviços ms-notifications, ms-chat e os Módulos 1 e 2."
        ),
        version="0.1.0",
    )

    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    register_exception_handlers(app)

    app.include_router(health_router)

    from app.dashboard.router import router as dashboard_router
    from app.notifications.router import router as notifications_router
    from app.notifications.router import ws_router as notifications_ws_router

    from app.chat.router import router as chat_router
    from app.chat.router import ws_router as chat_ws_router

    app.include_router(dashboard_router)
    app.include_router(notifications_router)
    app.include_router(notifications_ws_router)
    app.include_router(chat_router)
    app.include_router(chat_ws_router)

    if settings.dev_login_enabled:
        from app.api.dev import router as dev_router

        app.include_router(dev_router)

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {"service": settings.app_name, "status": "ok"}

    return app


app = create_app()
