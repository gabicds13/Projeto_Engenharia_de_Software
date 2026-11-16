"""Cliente de leitura das tendências globais do Módulo 5.

O feed /em-alta não representa dados específicos de um projeto.
A integração é somente leitura, backend-to-backend, sem tokens de outros grupos.
"""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit

import httpx


class CuradoriaUnavailable(Exception):
    """Feed remoto indisponível ou resposta inválida."""


def _https_url(value: object) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise CuradoriaUnavailable("URL inválida no feed do Módulo 5.")
    try:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("URL insegura")
    except ValueError as exc:
        raise CuradoriaUnavailable("URL inválida no feed do Módulo 5.") from exc
    return value


async def fetch_em_alta(*, base_url: str, timeout: float, limit: int = 6) -> dict:
    """Lê artigos reais classificados por recência/relevância pelo Módulo 5."""
    _https_url(base_url)
    if not 1 <= limit <= 10:
        raise CuradoriaUnavailable("Limite inválido.")
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}/em-alta",
                params={"limite": limit},
            )
        if response.status_code != 200:
            raise CuradoriaUnavailable("O Módulo 5 não respondeu com sucesso.")
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise CuradoriaUnavailable("Não foi possível ler o Módulo 5.") from exc

    if not isinstance(data, dict) or not isinstance(data.get("artigos"), list):
        raise CuradoriaUnavailable("Feed inválido do Módulo 5.")
    if len(data["artigos"]) > limit:
        raise CuradoriaUnavailable("Feed acima do limite solicitado.")
    articles = []
    for item in data["artigos"]:
        if not isinstance(item, dict):
            raise CuradoriaUnavailable("Artigo inválido.")
        title, source, category = item.get("titulo"), item.get("fonte"), item.get("categoria")
        if any(not isinstance(v, str) or not v.strip() or len(v) > 300
               for v in (title, source, category)):
            raise CuradoriaUnavailable("Metadados inválidos.")
        link = _https_url(item.get("link"))
        date = item.get("data_publicacao")
        if date is not None and (not isinstance(date, str) or len(date) > 40):
            raise CuradoriaUnavailable("Data de publicação inválida.")
        articles.append({
            "title": title,
            "url": link,
            "source": source,
            "category": category,
            "published_at": date,
        })

    updated = data.get("atualizado_em")
    if not isinstance(updated, str):
        raise CuradoriaUnavailable("Data de atualização ausente.")
    try:
        date = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        if date.tzinfo is None:
            raise ValueError("Sem fuso")
    except ValueError as exc:
        raise CuradoriaUnavailable("Data de atualização inválida.") from exc

    return {
        "source": "module-5",
        "scope": "global",
        "updated_at": updated,
        "articles": articles,
    }
