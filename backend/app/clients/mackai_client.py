"""Consulta autenticada das métricas do MackAI (Módulo 7).

Repassa somente o Bearer da pessoa autenticada pelo Módulo 1. Nunca usa
credencial global, nem envia o token na URL ou em logs.
"""
from __future__ import annotations

import httpx

from app.domain.schemas import MackaiMetrics


class MackaiUnavailable(Exception):
    """Falha controlada; métricas do Módulo 7 não derrubam o Dashboard."""


async def fetch_mackai_metrics(
    *, base_url: str, project_id: str, access_token: str, timeout: float
) -> MackaiMetrics:
    if not access_token:
        raise MackaiUnavailable("Token ausente.")
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}/api/projects/{project_id}/metrics",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            metrics = MackaiMetrics.model_validate(data)
            if metrics.project_id != project_id:
                raise MackaiUnavailable("Projeto divergente na resposta do Módulo 7.")
            return metrics
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise MackaiUnavailable("Métricas do MackAI indisponíveis.") from exc
