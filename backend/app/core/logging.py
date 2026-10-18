"""Logs estruturados em JSON com correlation id por requisição."""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

# correlation_id corrente (propagado via contextvar entre await's da mesma requisição)
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)

CORRELATION_HEADER = "X-Correlation-ID"


class JsonFormatter(logging.Formatter):
    """Formata cada registro de log como uma linha JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Campos extras passados via logger.info(..., extra={...})
        for key, value in getattr(record, "extra_fields", {}).items():
            payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Garante um correlation id por requisição e o devolve no header de resposta."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._logger = logging.getLogger("bff.request")

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        incoming = request.headers.get(CORRELATION_HEADER)
        cid = incoming or str(uuid.uuid4())
        token = correlation_id_var.set(cid)
        try:
            response = await call_next(request)
        finally:
            correlation_id_var.reset(token)
        response.headers[CORRELATION_HEADER] = cid
        return response


def get_correlation_id() -> str:
    return correlation_id_var.get()
