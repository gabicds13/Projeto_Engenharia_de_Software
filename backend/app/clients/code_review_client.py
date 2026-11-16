"""Leitura restrita do histórico de revisões do Módulo 4.

O /api/historico do M4 é global e limitado às últimas 20 revisões.
Antes de consultar esse histórico, usamos o M2 para descobrir os
repositórios associados ao projeto e visíveis para o usuário logado.
Somente revisões de PRs desses repositórios são devolvidas ao frontend.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime

import httpx


class CodeReviewUnavailable(Exception):
    """Contrato remoto não disponível ou insuficiente para uma leitura segura."""


_REPOSITORY = re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+")
_GITHUB_PR = re.compile(
    r"https://github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)/pull/([1-9][0-9]{0,18})/?",
    re.IGNORECASE,
)


async def project_repository_names(
    *,
    github_url: str,
    project_id: str,
    access_token: str,
    timeout: float,
) -> set[str]:
    """Busca no M2 a lista de repositórios do projeto (Bearer individual do M1)."""
    if not access_token:
        raise CodeReviewUnavailable("Sessão sem token para consultar o Módulo 2.")

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.get(
                f"{github_url.rstrip('/')}/api/v1/repositories",
                params={"project_id": project_id},
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if response.status_code != 200:
            raise CodeReviewUnavailable("Repositórios do projeto indisponíveis no Módulo 2.")
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise CodeReviewUnavailable("Não foi possível consultar o Módulo 2.") from exc

    if not isinstance(payload, list) or len(payload) > 10:
        raise CodeReviewUnavailable("Lista de repositórios inválida no Módulo 2.")

    names: set[str] = set()
    for item in payload:
        if not isinstance(item, dict) or str(item.get("project_id")) != project_id:
            raise CodeReviewUnavailable("Repositório não pertence ao projeto consultado.")
        name = item.get("full_name")
        if not isinstance(name, str):
            owner, repo = item.get("owner"), item.get("name")
            if not isinstance(owner, str) or not isinstance(repo, str):
                raise CodeReviewUnavailable("Identificação do repositório inválida.")
            name = f"{owner}/{repo}"
        if not _REPOSITORY.fullmatch(name) or name.split("/")[1] in {".", ".."}:
            raise CodeReviewUnavailable("Nome de repositório inválido.")
        names.add(name.lower())

    if not names:
        raise CodeReviewUnavailable("Nenhum repositório do projeto disponível no Módulo 2.")
    return names


class HttpCodeReviewClient:
    """Consulta a API do M4 somente pelo BFF, sem expor Basic Auth no navegador."""

    def __init__(self, *, base_url: str, username: str, password: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self._password = password
        self.timeout = timeout

    async def history(self, allowed_repositories: set[str]) -> list[dict]:
        """Devolve apenas metadados mínimos de PRs pertencentes ao projeto."""
        if not self.username or not self._password or not allowed_repositories:
            raise CodeReviewUnavailable("Credenciais ou repositórios do projeto ausentes.")
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=False
            ) as client:
                response = await client.get(
                    f"{self.base_url}/api/historico",
                    auth=httpx.BasicAuth(self.username, self._password),
                )
            if response.status_code != 200:
                raise CodeReviewUnavailable("Histórico do Módulo 4 indisponível.")
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise CodeReviewUnavailable("Não foi possível ler o histórico do Módulo 4.") from exc

        if not isinstance(payload, list) or len(payload) > 20:
            raise CodeReviewUnavailable("Formato inesperado no histórico do Módulo 4.")

        selected: list[dict] = []
        for item in payload:
            if not isinstance(item, dict):
                raise CodeReviewUnavailable("Revisão inválida no histórico do Módulo 4.")
            pr = item.get("pr")
            if not isinstance(pr, dict) or not isinstance(pr.get("url"), str):
                # Revisões de arquivos avulsos não têm vínculo verificável com projeto.
                continue
            match = _GITHUB_PR.fullmatch(pr["url"])
            if not match:
                continue
            full_name = f"{match.group(1)}/{match.group(2)}".lower()
            if full_name not in allowed_repositories:
                continue

            try:
                created = item["criado_em"]
                if not isinstance(created, str):
                    raise ValueError("Data inválida")
                reviewed_at = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if reviewed_at.tzinfo is None:
                    raise ValueError("Data sem timezone")
                identifier = item["id"]
                findings = item["achados"]
                if not isinstance(identifier, str) or not identifier or len(identifier) > 100:
                    raise ValueError("ID inválido")
                if not isinstance(findings, list) or len(findings) > 10_000:
                    raise ValueError("Achados inválidos")
                counts: Counter[str] = Counter()
                for finding in findings:
                    if not isinstance(finding, dict):
                        raise ValueError("Achado inválido")
                    severity = finding.get("gravidade")
                    if severity not in ("Alta", "Média", "Baixa"):
                        raise ValueError("Gravidade inválida")
                    counts[severity] += 1
                architecture = item["arquitetura"]
                if not isinstance(architecture, str) or len(architecture) > 40:
                    raise ValueError("Arquitetura inválida")
            except (KeyError, ValueError, TypeError) as exc:
                raise CodeReviewUnavailable("Dados de revisão inválidos no Módulo 4.") from exc

            selected.append(
                {
                    "id": identifier,
                    "reviewed_at": reviewed_at.isoformat(),
                    "pr_url": pr["url"],
                    "architecture": architecture,
                    "findings_count": len(findings),
                    "severity_counts": dict(counts),
                }
            )
        return selected
