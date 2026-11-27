"""Rotas somente GET para projetos, artefatos e análises do Módulo 3.

A API pública do M3 não exige login. O portal M6 continua exigindo JWT válido
e autorização de projeto no BFF antes de consultar qualquer dado de um projeto.
"""
from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Depends, Query, Response

from app.clients.module3_client import Module3Client, safe_segment
from app.clients.projects_client import ensure_project_access, list_accessible_project_ids
from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError, ServiceUnavailableError
from app.core.security import CurrentUser, get_current_user

router = APIRouter(prefix="/api/bff/module3", tags=["module3-artifacts"])


def _client(settings: Settings) -> Module3Client:
    if not settings.module3_enabled:
        raise ServiceUnavailableError("Integração com o Módulo 3 não está habilitada.")
    return Module3Client(settings)


def _items(payload: object, *keys: str) -> list[dict]:
    if isinstance(payload, list):
        data = payload
    elif isinstance(payload, dict):
        data = next((payload[k] for k in keys if isinstance(payload.get(k), list)), None)
    else:
        data = None
    if data is None or not all(isinstance(entry, dict) for entry in data):
        raise ServiceUnavailableError("Resposta do Módulo 3 incompatível com a lista esperada.")
    return data


def _analysis_ids(version: dict) -> set[str]:
    ids = set()
    for key in ("analysis_id", "latest_analysis_id"):
        value = version.get(key)
        if isinstance(value, (str, int)):
            ids.add(str(value))
    for key in ("analysis", "analyses"):
        value = version.get(key)
        entries = value if isinstance(value, list) else [value]
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("id"), (str, int)):
                ids.add(str(entry["id"]))
            elif isinstance(entry, (str, int)):
                ids.add(str(entry))
    return ids


def _project_links(settings: Settings) -> dict[str, str]:
    """Associa IDs M1 a M3 somente por configuração explícita do backend.

    Nunca aceita um ID M3 informado pelo navegador como substituto da autorização M1.
    """
    links: dict[str, str] = {}
    claimed_m3_ids: set[str] = set()
    for item in settings.effective_module3_project_map.split(","):
        item = item.strip()
        if not item:
            continue
        if item.count("=") != 1:
            raise ServiceUnavailableError("Configuração de projetos M1/M3 inválida.")
        m1_id, m3_id = (part.strip() for part in item.split("=", 1))
        # Validação estrita mesmo para mapeamentos vindos do ambiente.
        try:
            safe_segment(m1_id)
            safe_segment(m3_id)
        except NotFoundError as exc:
            raise ServiceUnavailableError("Configuração de projetos M1/M3 inválida.") from exc
        if m1_id in links or m3_id in claimed_m3_ids:
            raise ServiceUnavailableError("Mapeamento de projetos M1/M3 duplicado.")
        links[m1_id] = m3_id
        claimed_m3_ids.add(m3_id)
    return links


def _module3_project_id(m1_project_id: str, settings: Settings) -> str:
    links = _project_links(settings)
    if m1_project_id in links:
        return links[m1_project_id]
    # Não permitir que uma associação explícita seja alcançada pelo ID M3
    # através de outro projeto de identidade com o mesmo identificador.
    if m1_project_id in links.values():
        raise NotFoundError("Projeto sem associação disponível no Módulo 3.")
    return m1_project_id


async def _access(project_id: str, user: CurrentUser, settings: Settings) -> str:
    """Autoriza o ID M1 antes de traduzir para o ID público do M3."""
    await ensure_project_access(project_id, user, settings)
    return _module3_project_id(project_id, settings)


@router.get("/projects")
async def projects(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    # Lista do M3 é filtrada por projetos do usuário no M1.
    allowed = set(await list_accessible_project_ids(user, settings))
    if not allowed:
        return []
    data = await _client(settings).get_json("/projects/")
    by_source = {
        str(project.get("id") or project.get("project_id") or ""): project
        for project in _items(data, "items", "projects", "results")
    }
    result = []
    for m1_id in sorted(allowed):
        try:
            m3_id = _module3_project_id(m1_id, settings)
        except NotFoundError:
            continue
        if m3_id not in by_source:
            continue
        project = by_source[m3_id]
        result.append({
            **project,
            "id": m1_id,
            "project_id": m1_id,
            "module3_project_id": m3_id,
        })
    return result


@router.get("/projects/{project_id}")
async def project_detail(
    project_id: str,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    m3_id = await _access(project_id, user, settings)
    result = await _client(settings).get_json("/projects/" + safe_segment(m3_id))
    if not isinstance(result, dict):
        raise ServiceUnavailableError("Resposta de projeto do Módulo 3 inválida.")
    return {**result, "id": project_id, "project_id": project_id, "module3_project_id": m3_id}


@router.get("/projects/{project_id}/artifacts")
async def artifacts(
    project_id: str,
    search: str | None = Query(None, max_length=120),
    artifact_type: str | None = Query(None, pattern="^(PDF|MARKDOWN|PNG|JPEG)$"),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    m3_id = await _access(project_id, user, settings)
    params = {}
    if search:
        params["search"] = search
    if artifact_type:
        params["artifact_type"] = artifact_type
    return await _client(settings).get_json(
        "/projects/" + safe_segment(m3_id) + "/artifacts/",
        params=params or None,
    )


@router.get("/projects/{project_id}/artifacts/{artifact_id}/versions")
async def versions(
    project_id: str,
    artifact_id: str,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    m3_id = await _access(project_id, user, settings)
    return await _client(settings).get_json(
        "/projects/" + safe_segment(m3_id) + "/artifacts/" +
        safe_segment(artifact_id) + "/versions"
    )


@router.get("/projects/{project_id}/artifacts/{artifact_id}/analyses/{analysis_id}")
async def existing_analysis(
    project_id: str,
    artifact_id: str,
    analysis_id: str,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Nunca aceita ID de análise arbitrário: deve estar vinculado a uma versão."""
    m3_id = await _access(project_id, user, settings)
    client = _client(settings)
    path = (
        "/projects/" + safe_segment(m3_id) + "/artifacts/" +
        safe_segment(artifact_id) + "/versions"
    )
    data = await client.get_json(path)
    entries = _items(data, "items", "versions", "results")
    if not any(safe_segment(analysis_id) in _analysis_ids(item) for item in entries):
        raise NotFoundError("A análise não está vinculada às versões deste artefato.")
    return await client.get_json("/analyses/" + safe_segment(analysis_id))


@router.get("/projects/{project_id}/artifacts/{artifact_id}/download")
async def download_artifact(
    project_id: str,
    artifact_id: str,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    m3_id = await _access(project_id, user, settings)
    path = (
        "/projects/" + safe_segment(m3_id) + "/artifacts/" +
        safe_segment(artifact_id) + "/download"
    )
    content, content_type = await _client(settings).download(path)
    mime = content_type.split(";", 1)[0].strip().lower()
    extension = mimetypes.guess_extension(mime) or ".bin"
    name = "artefato-" + artifact_id + extension
    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": 'attachment; filename="' + name + '"'},
    )
