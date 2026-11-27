"""Cliente somente-leitura para o serviço de Artefatos do Módulo 3."""
from __future__ import annotations

from urllib.parse import quote
import re

import httpx

from app.core.config import Settings
from app.core.errors import NotFoundError, ServiceUnavailableError

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_MAX_FILE_BYTES = 20 * 1024 * 1024


def safe_segment(identifier: str) -> str:
    """Evita traversal, barras e parâmetros arbitrários na URL do upstream."""
    if not _ID_RE.fullmatch(identifier) or identifier in {".", ".."}:
        raise NotFoundError("Identificador de artefato ou projeto inválido.")
    return quote(identifier, safe="")


class Module3Client:
    def __init__(self, settings: Settings):
        if not settings.module3_url.startswith("https://"):
            raise ServiceUnavailableError("O Módulo 3 deve ser configurado com HTTPS.")
        self._base_url = settings.module3_url.rstrip("/")
        self._timeout = settings.module3_timeout_seconds

    async def get_json(self, path: str, params: dict[str, str] | None = None) -> object:
        """Não encaminha JWT do Módulo 1 nem credenciais de outro módulo."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as client:
                response = await client.get(self._base_url + path, params=params)
            self._check_status(response.status_code)
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ServiceUnavailableError("Não foi possível consultar o Módulo 3.") from exc

    async def download(self, path: str) -> tuple[bytes, str]:
        """Baixa até 20 MiB e impede crescimento de memória sem limite."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as client:
                async with client.stream("GET", self._base_url + path) as response:
                    self._check_status(response.status_code)
                    content_type = response.headers.get("content-type", "application/octet-stream")
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(data) + len(chunk) > _MAX_FILE_BYTES:
                            raise ServiceUnavailableError("Arquivo do Módulo 3 acima de 20 MiB.")
                        data.extend(chunk)
                    return bytes(data), content_type
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError("Não foi possível baixar o artefato do Módulo 3.") from exc

    @staticmethod
    def _check_status(status_code: int) -> None:
        if status_code == 404:
            raise NotFoundError("Registro não encontrado no Módulo 3.")
        if status_code != 200:
            raise ServiceUnavailableError("O serviço do Módulo 3 não respondeu corretamente.")
