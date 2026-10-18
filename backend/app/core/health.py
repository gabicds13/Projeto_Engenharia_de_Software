"""Health checks: liveness (/health) e readiness (/ready).

Importante: o readiness reflete apenas o próprio BFF. A indisponibilidade de um
serviço downstream (ms-notifications, ms-chat, Módulos 1/2) é tratada por
degradação graciosa e NÃO deve marcar o portal como "not ready" — caso contrário
a falha de um terceiro derrubaria o portal, violando o requisito de robustez.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: o processo está de pé."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict[str, str]:
    """Readiness: o BFF está pronto para servir (não depende de downstreams)."""
    return {"status": "ready"}
