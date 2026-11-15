"""Módulo 2 GitHubSync: traduz a API real por repositório em métricas por projeto.

O Módulo 2 protege dados por usuário e aceita o Bearer RS256 do Módulo 1.
Os números nunca são substituídos silenciosamente por mocks quando uma chamada falha.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Protocol

import httpx

from app.clients.base import UpstreamError, raise_for_status
from app.domain.schemas import WeeklyPoint, WeeklySeries


class GithubClient(Protocol):
    async def weekly_commits_prs(self, project_id: str) -> WeeklySeries: ...
    async def open_prs(self, project_id: str) -> int: ...
    async def commits_this_week(self, project_id: str) -> int: ...


class MockGithubClient:
    async def weekly_commits_prs(self, project_id: str) -> WeeklySeries:
        return WeeklySeries(
            points=[
                WeeklyPoint(week="2026-W37", commits=42, prs=6),
                WeeklyPoint(week="2026-W38", commits=51, prs=8),
                WeeklyPoint(week="2026-W39", commits=38, prs=5),
                WeeklyPoint(week="2026-W40", commits=63, prs=9),
                WeeklyPoint(week="2026-W41", commits=47, prs=7),
            ]
        )

    async def open_prs(self, project_id: str) -> int:
        return 7

    async def commits_this_week(self, project_id: str) -> int:
        return 47


# Limites explícitos: um truncamento não pode virar uma métrica aparentemente real.
_MAX_REPOSITORIES = 10
_MAX_PAGES_PER_REPOSITORY = 10


class HttpGithubClient:
    """Consumidor do contrato de produção do Módulo 2.

    GET /api/v1/repositories?project_id=<uuid> -> lista de repositórios visíveis
    GET /api/v1/metrics/dashboard?repository_id=<id>&days=7 -> KPIs por repo
    GET /api/v1/commits?repository_id=<id>&since=<iso>&page=N -> lista paginada
    GET /api/v1/pull-requests?repository_id=<id>&page=N -> lista paginada

    O gráfico soma os commits (autoria) e os PRs (abertura) de cinco semanas
    ISO. Não usa o dashboard default do M2, que poderia ser outro projeto.
    """

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}

    async def _get(self, path: str, params: dict[str, object]) -> object:
        try:
            async with httpx.AsyncClient(headers=self._headers, timeout=5.0) as client:
                response = raise_for_status(
                    await client.get(f"{self._base_url}{path}", params=params)
                )
                return response.json()
        except httpx.HTTPError as exc:
            raise UpstreamError("Módulo 2 não respondeu à requisição.") from exc
        except ValueError as exc:
            raise UpstreamError("Resposta JSON inválida do Módulo 2.") from exc

    @staticmethod
    def _non_negative_int(data: dict, key: str) -> int:
        value = data.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise UpstreamError(f"Campo {key} inválido no Módulo 2.")
        return value

    async def _repository_ids(self, project_id: str) -> list[int]:
        payload = await self._get(
            "/api/v1/repositories",
            {"project_id": project_id},
        )
        if not isinstance(payload, list):
            raise UpstreamError("Lista de repositórios inválida no Módulo 2.")
        if not payload:
            # Repositórios M2 ainda são restritos ao proprietário do vínculo.
            # Ausência de fonte não é sinônimo de zero atividade.
            raise UpstreamError("Nenhum repositório acessível neste projeto no Módulo 2.")
        if len(payload) > _MAX_REPOSITORIES:
            raise UpstreamError("Quantidade de repositórios excede o limite do agregador.")

        ids = []
        for repo in payload:
            if not isinstance(repo, dict) or str(repo.get("project_id")) != project_id:
                raise UpstreamError("Módulo 2 retornou repositório fora do projeto.")
            ids.append(self._non_negative_int(repo, "id"))
        if len(ids) != len(set(ids)):
            raise UpstreamError("Repositórios duplicados no Módulo 2.")
        return ids

    async def _summary(self, repo_id: int) -> dict:
        payload = await self._get(
            "/api/v1/metrics/dashboard",
            {"repository_id": repo_id, "days": 7},
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("repository"), dict):
            raise UpstreamError("KPIs inválidos no Módulo 2.")
        if payload["repository"].get("id") != repo_id or payload.get("period_days") != 7:
            raise UpstreamError("KPIs do Módulo 2 não correspondem ao repositório/período.")
        return payload

    async def _summaries(self, project_id: str) -> list[dict]:
        ids = await self._repository_ids(project_id)
        return await asyncio.gather(*(self._summary(repo_id) for repo_id in ids))

    async def commits_this_week(self, project_id: str) -> int:
        """Retorna a métrica real de commits dos últimos 7 dias (janela móvel)."""
        summaries = await self._summaries(project_id)
        return sum(self._non_negative_int(item, "total_commits") for item in summaries)

    async def open_prs(self, project_id: str) -> int:
        """PRs atualmente abertos em todos os repositórios vinculados ao projeto."""
        summaries = await self._summaries(project_id)
        return sum(self._non_negative_int(item, "prs_open") for item in summaries)

    async def _all_pages(
        self, path: str, repo_id: int, **extra: object
    ) -> list[dict]:
        items: list[dict] = []
        for page in range(1, _MAX_PAGES_PER_REPOSITORY + 1):
            payload = await self._get(
                path,
                {"repository_id": repo_id, "page": page, **extra},
            )
            if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
                raise UpstreamError("Paginação inválida no Módulo 2.")
            results = payload["results"]
            if any(not isinstance(item, dict) for item in results):
                raise UpstreamError("Item de métrica inválido no Módulo 2.")
            items.extend(results)
            next_page = payload.get("next")
            if next_page is None or next_page == "":
                return items
            if not isinstance(next_page, str):
                raise UpstreamError("Próxima página inválida no Módulo 2.")
            # Não seguir URL remota informada no payload; incrementa somente
            # o parâmetro 'page' no host configurado do Módulo 2.
        raise UpstreamError("Paginação acima do limite; gráfico indisponível.")

    @staticmethod
    def _datetime_field(item: dict, key: str) -> datetime:
        raw = item.get(key)
        if not isinstance(raw, str):
            raise UpstreamError(f"Campo {key} ausente no evento do Módulo 2.")
        try:
            date = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if date.tzinfo is None:
                raise ValueError("timestamp sem timezone")
            return date.astimezone(UTC)
        except ValueError as exc:
            raise UpstreamError(f"Data {key} inválida no Módulo 2.") from exc

    async def weekly_commits_prs(self, project_id: str) -> WeeklySeries:
        repo_ids = await self._repository_ids(project_id)
        now = datetime.now(UTC)
        current_monday = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        start = current_monday - timedelta(weeks=4)
        weeks = [start + timedelta(weeks=i) for i in range(5)]
        totals = {
            week.isocalendar()[:2]: {"commits": 0, "prs": 0}
            for week in weeks
        }

        # O M2 não publica série semanal por projeto. Calculamos a série a
        # partir de seus fatos reais, sem inventar dados ou ignorar paginação.
        requests = []
        for repo_id in repo_ids:
            requests.extend((
                self._all_pages(
                    "/api/v1/commits", repo_id,
                    since=start.isoformat(),
                ),
                self._all_pages("/api/v1/pull-requests", repo_id),
            ))
        results = await asyncio.gather(*requests)
        for index, events in enumerate(results):
            field = "authored_at" if index % 2 == 0 else "opened_at"
            metric = "commits" if index % 2 == 0 else "prs"
            for item in events:
                event_date = self._datetime_field(item, field)
                if start <= event_date <= now:
                    bucket = event_date.isocalendar()[:2]
                    if bucket in totals:
                        totals[bucket][metric] += 1

        return WeeklySeries(
            points=[
                WeeklyPoint(
                    week=f"{week.isocalendar().year}-W{week.isocalendar().week:02d}",
                    commits=totals[week.isocalendar()[:2]]["commits"],
                    prs=totals[week.isocalendar()[:2]]["prs"],
                )
                for week in weeks
            ]
        )
