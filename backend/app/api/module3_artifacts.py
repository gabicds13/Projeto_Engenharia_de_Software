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


async def _access(project_id: str, user: CurrentUser, settings: Settings) -> None:
    await ensure_project_access(project_id, user, settings)


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
    return [
        project for project in _items(data, "items", "projects", "results")
        if str(project.get("id") or project.get("project_id") or "") in allowed
    ]


@router.get("/projects/{project_id}")
async def project_detail(
    project_id: str,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    await _access(project_id, user, settings)
    return await _client(settings).get_json("/projects/" + safe_segment(project_id))


@router.get("/projects/{project_id}/artifacts")
async def artifacts(
    project_id: str,
    search: str | None = Query(None, max_length=120),
    artifact_type: str | None = Query(None, pattern="^(PDF|MARKDOWN|PNG|JPEG)$"),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    await _access(project_id, user, settings)
    params = {}
    if search:
        params["search"] = search
    if artifact_type:
        params["artifact_type"] = artifact_type
    return await _client(settings).get_json(
        "/projects/" + safe_segment(project_id) + "/artifacts/",
        params=params or None,
    )


@router.get("/projects/{project_id}/artifacts/{artifact_id}/versions")
async def versions(
    project_id: str,
    artifact_id: str,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    await _access(project_id, user, settings)
    return await _client(settings).get_json(
        "/projects/" + safe_segment(project_id) + "/artifacts/" +
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
    await _access(project_id, user, settings)
    client = _client(settings)
    path = (
        "/projects/" + safe_segment(project_id) + "/artifacts/" +
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
    await _access(project_id, user, settings)
    path = (
        "/projects/" + safe_segment(project_id) + "/artifacts/" +
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
