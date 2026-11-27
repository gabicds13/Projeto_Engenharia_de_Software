"""Contrato M6/M3: acesso controlado, somente GET e respostas isoladas."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import jwt

from app.core.config import Settings, get_settings
import app.api.module3_artifacts as api
from app.core.errors import ServiceUnavailableError


def _headers(projects=("p-123",), role="PM"):
    config = get_settings()
    now = datetime.now(UTC)
    token = jwt.encode({
        "sub": "user-test", "role": role,
        "project_ids": list(projects), "iat": now,
        "exp": now + timedelta(hours=1),
    }, config.jwt_secret, algorithm=config.jwt_algorithm)
    return {"Authorization": "Bearer " + token}


class FakeModule3:
    calls: list[tuple[str, dict | None]] = []

    def __init__(self, settings):
        pass

    async def get_json(self, path, params=None):
        self.calls.append((path, params))
        if path == "/projects/":
            return {"items": [{"id": "p-123", "name": "Permitido"}, {"id": "p-999", "name": "Outro"}]}
        if path == "/projects/p-123":
            return {"id": "p-123", "name": "Permitido"}
        if path == "/projects/p-123/artifacts/":
            return {"items": [{"id": "a-1", "name": "Requisitos", "artifact_type": "PDF"}]}
        if path == "/projects/p-123/artifacts/a-1/versions":
            return {"versions": [{"id": "v-1", "analysis_id": "analysis-42"}]}
        if path == "/analyses/analysis-42":
            return {"id": "analysis-42", "status": "COMPLETED", "classification": "user_story",
                    "summary": "Resumo de exemplo."}
        raise AssertionError("Unexpected upstream GET: " + path)

    async def download(self, path):
        self.calls.append((path, None))
        return (b"%PDF-demo", "application/pdf")


def test_module3_requires_login_and_project_access(client, monkeypatch):
    FakeModule3.calls = []
    monkeypatch.setattr(api, "Module3Client", FakeModule3)
    assert client.get("/api/bff/module3/projects").status_code == 401
    assert client.get("/api/bff/module3/projects/p-999/artifacts", headers=_headers()).status_code == 403
    assert FakeModule3.calls == []


def test_projects_are_filtered_by_access(client, monkeypatch):
    FakeModule3.calls = []
    monkeypatch.setattr(api, "Module3Client", FakeModule3)
    r = client.get("/api/bff/module3/projects", headers=_headers())
    assert r.status_code == 200
    assert [row["id"] for row in r.json()] == ["p-123"]


def test_filters_versions_and_existing_analysis(client, monkeypatch):
    FakeModule3.calls = []
    monkeypatch.setattr(api, "Module3Client", FakeModule3)
    base = "/api/bff/module3/projects/p-123/artifacts"
    r = client.get(base, params={"search": "Requi", "artifact_type": "PDF"}, headers=_headers())
    assert r.status_code == 200
    assert FakeModule3.calls[-1] == ("/projects/p-123/artifacts/", {"search": "Requi", "artifact_type": "PDF"})
    assert client.get(base + "?artifact_type=DOCX", headers=_headers()).status_code == 422
    assert client.get(base + "/a-1/versions", headers=_headers()).status_code == 200
    r = client.get(base + "/a-1/analyses/analysis-42", headers=_headers())
    assert r.status_code == 200 and r.json()["classification"] == "user_story"
    r = client.get(base + "/a-1/analyses/analysis-999", headers=_headers())
    assert r.status_code == 404
    assert not any(call[0] == "/analyses/analysis-999" for call in FakeModule3.calls)


def test_download_requires_project_access(client, monkeypatch):
    FakeModule3.calls = []
    monkeypatch.setattr(api, "Module3Client", FakeModule3)
    path = "/api/bff/module3/projects/p-123/artifacts/a-1/download"
    assert client.get(path, headers=_headers(projects=("p-888",))).status_code == 403
    response = client.get(path, headers=_headers())
    assert response.status_code == 200
    assert response.content == b"%PDF-demo"
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"].startswith("attachment;")


def test_upstream_failure_is_isolated(client, monkeypatch):
    class Down:
        def __init__(self, settings):
            pass
        async def get_json(self, path, params=None):
            raise ServiceUnavailableError("Modulo 3 indisponivel.")
    monkeypatch.setattr(api, "Module3Client", Down)
    response = client.get("/api/bff/module3/projects", headers=_headers())
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
    assert client.get("/health").status_code == 200



def test_explicit_mapping_uses_m1_identity_and_m3_artifact_source(client, monkeypatch):
    """Token só autoriza M1; projeto numérico M3 vem de configuração do servidor."""
    m1_id = "f092329c-0747-4b88-92f0-c3036786ce91"
    class MappedModule3:
        calls = []
        def __init__(self, settings):
            pass
        async def get_json(self, path, params=None):
            self.calls.append(path)
            if path == "/projects/":
                return [{"id": 3, "name": "Projeto Teste26112026"}, {"id": 2, "name": "Outro"}]
            if path == "/projects/3/artifacts/":
                return [{"id": 12, "name": "testeDile.md", "artifact_type": "MARKDOWN"}]
            if path == "/projects/3/artifacts/12/versions":
                return [{"id": 44, "version_number": 2}]
            if path == "/projects/3":
                return {"id": 3, "name": "Projeto Teste26112026"}
            raise AssertionError("Unexpected path " + path)
    MappedModule3.calls = []
    monkeypatch.setattr(api, "Module3Client", MappedModule3)
    client.app.dependency_overrides[get_settings] = lambda: Settings(module3_project_map=f"{m1_id}=3")
    try:
        r = client.get("/api/bff/module3/projects", headers=_headers(projects=(m1_id,)))
        assert r.status_code == 200
        assert r.json() == [{
            "id": m1_id, "project_id": m1_id, "module3_project_id": "3",
            "name": "Projeto Teste26112026",
        }]
        r = client.get(f"/api/bff/module3/projects/{m1_id}/artifacts", headers=_headers(projects=(m1_id,)))
        assert r.status_code == 200
        assert r.json()[0]["name"] == "testeDile.md"
        assert client.get(f"/api/bff/module3/projects/{m1_id}/artifacts/12/versions", headers=_headers(projects=(m1_id,))).status_code == 200
        assert client.get(f"/api/bff/module3/projects/{m1_id}", headers=_headers(projects=(m1_id,))).json()["module3_project_id"] == "3"
        assert "/projects/3/artifacts/" in MappedModule3.calls
        # '3' não passa a ser um projeto do M1 ao configurar o vínculo.
        assert client.get("/api/bff/module3/projects/3/artifacts", headers=_headers(projects=(m1_id,))).status_code == 403
        assert client.get(f"/api/bff/module3/projects/{m1_id}/artifacts", headers=_headers(projects=("other",))).status_code == 403
    finally:
        client.app.dependency_overrides.clear()


def test_duplicate_or_invalid_mapping_is_not_accepted(client, monkeypatch):
    FakeModule3.calls = []
    monkeypatch.setattr(api, "Module3Client", FakeModule3)
    for mapping in ("p-123=3,p-999=3", "p-123=../3", "p-123:3"):
        client.app.dependency_overrides[get_settings] = lambda mapping=mapping: Settings(module3_project_map=mapping)
        try:
            assert client.get("/api/bff/module3/projects", headers=_headers()).status_code == 503
        finally:
            client.app.dependency_overrides.clear()
