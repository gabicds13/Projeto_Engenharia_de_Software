"""Métricas públicas agregadas do M4; escopo global somente por solicitação explícita."""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

import httpx
from pydantic import BaseModel, Field

from app.clients.code_review_client import CodeReviewUnavailable

Count = Annotated[int, Field(strict=True, ge=0)]
Priority = Literal["critical", "high", "medium", "low"]


class DailyReviewMetrics(BaseModel):
    data: date
    revisoes: Count
    achados: Count


class CodeReviewMetrics(BaseModel):
    total_revisoes: Count
    total_achados: Count
    por_prioridade: dict[Priority, Count]
    por_categoria: dict[str, Count]
    por_arquitetura: dict[str, Count]
    revisoes_por_dia: list[DailyReviewMetrics] = Field(max_length=90)


async def fetch_code_review_metrics(
    *, base_url: str, project_id: str | None, days: int, timeout: float
) -> CodeReviewMetrics:
    if project_id == "" or not 1 <= days <= 90 or not base_url.startswith("https://"):
        raise CodeReviewUnavailable("Configuração inválida para métricas do M4.")

    params: dict[str, str | int] = {"dias": days}
    if project_id is not None:
        params["project_id"] = project_id

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}/api/dashboard/metricas",
                params=params,
            )
        if response.status_code != 200:
            raise CodeReviewUnavailable("Métricas do M4 indisponíveis.")
        payload = response.json()
        if not isinstance(payload, dict):
            raise CodeReviewUnavailable("Formato inválido das métricas do M4.")
        if project_id is None and ("project_id" not in payload or payload["project_id"] is not None):
            raise CodeReviewUnavailable("Escopo global não confirmado pelo M4.")
        if project_id is not None and str(payload.get("project_id")) != project_id:
            raise CodeReviewUnavailable("Projeto divergente nas métricas do M4.")
        metrics = CodeReviewMetrics.model_validate(payload)
        if sum(metrics.por_prioridade.values()) != metrics.total_achados:
            raise CodeReviewUnavailable("Contagens por prioridade inconsistentes no M4.")
        if len({row.data for row in metrics.revisoes_por_dia}) != len(metrics.revisoes_por_dia):
            raise CodeReviewUnavailable("Datas duplicadas nas métricas do M4.")
        metrics.revisoes_por_dia.sort(key=lambda row: row.data)
        return metrics
    except (httpx.HTTPError, ValueError) as exc:
        raise CodeReviewUnavailable("Não foi possível consultar as métricas do M4.") from exc
