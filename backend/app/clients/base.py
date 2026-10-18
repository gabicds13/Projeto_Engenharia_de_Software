"""Tipos comuns dos clients upstream."""
from __future__ import annotations

import httpx


class UpstreamError(Exception):
    """Falha ao chamar um serviço downstream (rede, status != 2xx, parsing)."""


def raise_for_status(response: httpx.Response) -> httpx.Response:
    if response.status_code >= 400:
        raise UpstreamError(f"status {response.status_code} de {response.request.url}")
    return response
