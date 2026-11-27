import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { api, downloadBffFile } from "../../lib/apiClient";
import {
  module3AnalysisId, module3Id, module3Items,
  type Module3Analysis, type Module3Artifact, type Module3Project, type Module3Version,
} from "./types";

function label(value: unknown): string {
  if (value == null || value === "") return "Não informado";
  return typeof value === "string" ? value : JSON.stringify(value);
}

function dateLabel(value: string | undefined): string {
  if (!value) return "";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("pt-BR");
}

export function ArtifactsPage() {
  const [projects, setProjects] = useState<Module3Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [projectError, setProjectError] = useState("");
  const [artifacts, setArtifacts] = useState<Module3Artifact[]>([]);
  const [loadingArtifacts, setLoadingArtifacts] = useState(false);
  const [artifactError, setArtifactError] = useState("");
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("");
  const [selectedArtifact, setSelectedArtifact] = useState("");
  const [versions, setVersions] = useState<Module3Version[]>([]);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [versionError, setVersionError] = useState("");
  const [analysis, setAnalysis] = useState<Module3Analysis | null>(null);
  const [analysisError, setAnalysisError] = useState("");
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [downloadError, setDownloadError] = useState("");
  const selectionRef = useRef(projectId);
  selectionRef.current = projectId;

  const loadProjects = useCallback(async () => {
    setLoadingProjects(true);
    setProjectError("");
    try {
      const response = await api.get<unknown>("/api/bff/module3/projects");
      const list = module3Items<Module3Project>(response, "items", "projects", "results");
      setProjects(list);
      const first = list.map(module3Id).find(Boolean) ?? "";
      setProjectId((current) => list.some(p => module3Id(p) === current) ? current : first);
    } catch {
      setProjects([]);
      setProjectId("");
      setProjectError("Não foi possível consultar os projetos do Módulo 3. Confira a conexão e tente novamente.");
    } finally {
      setLoadingProjects(false);
    }
  }, []);

  useEffect(() => { void loadProjects(); }, [loadProjects]);

  const loadArtifacts = useCallback(async (selected: string, query: string, type: string) => {
    if (!selected) return;
    setLoadingArtifacts(true);
    setArtifactError("");
    const params = new URLSearchParams();
    if (query.trim()) params.set("search", query.trim());
    if (type) params.set("artifact_type", type);
    try {
      const url = "/api/bff/module3/projects/" + encodeURIComponent(selected) + "/artifacts";
      const response = await api.get<unknown>(url + (params.size ? "?" + params : ""));
      if (selectionRef.current !== selected) return;
      setArtifacts(module3Items<Module3Artifact>(response, "items", "artifacts", "results"));
    } catch {
      if (selectionRef.current !== selected) return;
      setArtifacts([]);
      setArtifactError("Os artefatos não estão disponíveis agora. As outras áreas do portal continuam funcionando.");
    } finally {
      if (selectionRef.current === selected) setLoadingArtifacts(false);
    }
  }, []);

  useEffect(() => {
    setArtifacts([]);
    setSelectedArtifact("");
    setVersions([]);
    setAnalysis(null);
    setArtifactError("");
    setVersionError("");
    setAnalysisError("");
    if (projectId) void loadArtifacts(projectId, "", "");
  }, [projectId, loadArtifacts]);

  const onSearch = (event: FormEvent) => {
    event.preventDefault();
    setSelectedArtifact("");
    setVersions([]);
    setAnalysis(null);
    void loadArtifacts(projectId, search, kind);
  };

  const loadVersions = async (artifactId: string) => {
    setSelectedArtifact(artifactId);
    setVersions([]);
    setAnalysis(null);
    setVersionError("");
    setAnalysisError("");
    setLoadingVersions(true);
    try {
      const response = await api.get<unknown>(
        "/api/bff/module3/projects/" + encodeURIComponent(projectId) +
        "/artifacts/" + encodeURIComponent(artifactId) + "/versions",
      );
      setVersions(module3Items<Module3Version>(response, "items", "versions", "results"));
    } catch {
      setVersionError("Não foi possível consultar as versões deste artefato.");
    } finally {
      setLoadingVersions(false);
    }
  };

  const viewAnalysis = async (artifactId: string, analysisId: string) => {
    setAnalysis(null);
    setAnalysisError("");
    setLoadingAnalysis(true);
    try {
      setAnalysis(await api.get<Module3Analysis>(
        "/api/bff/module3/projects/" + encodeURIComponent(projectId) +
        "/artifacts/" + encodeURIComponent(artifactId) +
        "/analyses/" + encodeURIComponent(analysisId),
      ));
    } catch {
      setAnalysisError("Não foi possível consultar a análise existente no Módulo 3.");
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const download = async (artifactId: string) => {
    setDownloadError("");
    try {
      const blob = await downloadBffFile(
        "/api/bff/module3/projects/" + encodeURIComponent(projectId) +
        "/artifacts/" + encodeURIComponent(artifactId) + "/download",
      );
      const url = URL.createObjectURL(blob);
      try {
        const a = document.createElement("a");
        a.href = url;
        a.download = "artefato-" + artifactId;
        document.body.appendChild(a);
        a.click();
        a.remove();
      } finally {
        URL.revokeObjectURL(url);
      }
    } catch {
      setDownloadError("Não foi possível baixar o arquivo. Tente novamente.");
    }
  };

  return (
    <section className="flex flex-col gap-5" aria-label="Artefatos - Módulo 3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-text">Artefatos do projeto — Módulo 3</h1>
          <p className="mt-1 text-sm text-text-muted">Documentos e análises existentes, consultados pela API do Módulo 3.</p>
        </div>
        <a href="https://modulo3-fhgjdpa6d5bbfvff.canadacentral-01.azurewebsites.net/app/"
          target="_blank" rel="noopener noreferrer" className="rounded-md border border-border px-3 py-2 text-sm text-primary">
          Abrir Módulo 3
        </a>
      </div>

      {loadingProjects ? <p>Carregando projetos…</p> : projectError ? (
        <div role="alert" className="rounded-lg border border-border bg-surface p-4">
          {projectError}
          <button type="button" onClick={() => void loadProjects()} className="ml-3 text-primary underline">Tentar novamente</button>
        </div>
      ) : !projects.length ? (
        <p className="rounded-lg border border-border bg-surface p-5 text-sm text-text-muted">
          Nenhum projeto do Módulo 3 corresponde aos projetos autorizados do seu login.
          O Módulo 3 e o Módulo 1 precisam usar o mesmo identificador de projeto.
        </p>
      ) : (
        <>
          <label className="flex flex-col gap-1 text-sm font-medium text-text">
            Projeto
            <select value={projectId} onChange={event => setProjectId(event.target.value)}
              className="rounded-md border border-border bg-surface px-3 py-2 text-text">
              {projects.map(project => (
                <option key={module3Id(project)} value={module3Id(project)}>
                  {project.name ?? project.title ?? module3Id(project)}
                </option>
              ))}
            </select>
          </label>

          <form onSubmit={onSearch} className="flex flex-wrap items-end gap-3">
            <label className="flex min-w-[12rem] flex-1 flex-col gap-1 text-sm">
              Buscar artefatos
              <input value={search} onChange={event => setSearch(event.target.value)}
                maxLength={120} placeholder="Nome do documento"
                className="rounded-md border border-border bg-surface px-3 py-2 text-text" />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Tipo de arquivo
              <select value={kind} onChange={event => setKind(event.target.value)}
                className="rounded-md border border-border bg-surface px-3 py-2 text-text">
                <option value="">Todos</option>
                <option value="PDF">PDF</option>
                <option value="MARKDOWN">Markdown</option>
                <option value="PNG">PNG</option>
                <option value="JPEG">JPEG</option>
              </select>
            </label>
            <button type="submit" disabled={!projectId || loadingArtifacts}
              className="rounded-md bg-primary px-4 py-2 font-medium text-white disabled:opacity-60">Buscar</button>
          </form>

          {artifactError && <p role="alert" className="rounded-lg border border-border p-3 text-sm text-text-muted">{artifactError}</p>}
          {loadingArtifacts ? <p className="text-text-muted">Carregando artefatos…</p> :
            artifacts.length === 0 && !artifactError ? <p className="text-text-muted">Nenhum artefato encontrado para os filtros atuais.</p> : (
              <ul className="flex flex-col gap-3">
                {artifacts.map(item => {
                  const id = module3Id(item);
                  return (
                    <li key={id} className="rounded-lg border border-border bg-surface p-4">
                      <div className="flex flex-wrap justify-between gap-3">
                        <div>
                          <h2 className="font-semibold text-text">{item.name ?? item.filename ?? item.title ?? id}</h2>
                          <p className="mt-1 text-xs text-text-muted">
                            {item.artifact_type ?? "Tipo não informado"}
                            {item.created_at ? " · " + dateLabel(item.created_at) : ""}
                          </p>
                          {item.description && <p className="mt-2 text-sm text-text-muted">{item.description}</p>}
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <button type="button" onClick={() => void loadVersions(id)} className="rounded-md border border-border px-3 py-2 text-sm text-primary">Ver versões</button>
                          <button type="button" onClick={() => void download(id)} className="rounded-md border border-border px-3 py-2 text-sm text-primary">Baixar arquivo</button>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}

          {downloadError && <p role="alert" className="text-sm text-text-muted">{downloadError}</p>}
          {selectedArtifact && (
            <section className="rounded-lg border border-border bg-surface p-4" aria-label="Versões do artefato">
              <h2 className="text-lg font-semibold">Versões do artefato</h2>
              {loadingVersions ? <p className="mt-2">Consultando versões…</p> : versionError ? (
                <p role="alert" className="mt-2">{versionError}</p>
              ) : versions.length === 0 ? <p className="mt-2 text-sm text-text-muted">Nenhuma versão encontrada.</p> : (
                <ul className="mt-3 flex flex-col gap-2">
                  {versions.map((version) => {
                    const id = module3Id(version);
                    const analysisId = module3AnalysisId(version);
                    return (
                      <li key={id} className="flex flex-wrap items-center justify-between gap-3 border-b border-border py-2">
                        <span className="text-sm">Versão {version.version_number ?? id}{version.created_at ? " · " + dateLabel(version.created_at) : ""}</span>
                        {analysisId ? <button type="button" onClick={() => void viewAnalysis(selectedArtifact, analysisId)}
                          className="rounded-md border border-border px-3 py-2 text-sm text-primary">Ver análise existente</button> :
                          <span className="text-xs text-text-muted">Sem ID de análise disponível</span>}
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          )}
          {loadingAnalysis && <p>Carregando análise…</p>}
          {analysisError && <p role="alert" className="text-sm text-text-muted">{analysisError}</p>}
          {analysis && (
            <section aria-label="Análise do Módulo 3" className="rounded-lg border border-border bg-surface p-4">
              <h2 className="text-lg font-semibold">Análise de IA existente</h2>
              <p className="mt-1 text-xs text-text-muted">Consulta somente leitura; nenhuma nova análise foi solicitada.</p>
              <dl className="mt-3 grid gap-2 text-sm">
                <div><dt className="font-semibold">Status</dt><dd>{label(analysis.status)}</dd></div>
                {analysis.error_message && <div><dt className="font-semibold">Erro da análise</dt><dd>{analysis.error_message}</dd></div>}
                <div><dt className="font-semibold">Classificação</dt><dd>{label(analysis.classification)}</dd></div>
                <div><dt className="font-semibold">Confiança</dt><dd>{typeof analysis.confidence === "number" ? (analysis.confidence * 100).toFixed(1) + "%" : "Não informada"}</dd></div>
                <div><dt className="font-semibold">Resumo</dt><dd className="whitespace-pre-wrap break-words">{label(analysis.summary)}</dd></div>
                <div><dt className="font-semibold">Arquitetura identificada</dt><dd className="break-words">{label(analysis.architecture)}</dd></div>
                {analysis.classification_reason && <div><dt className="font-semibold">Justificativa</dt><dd>{analysis.classification_reason}</dd></div>}
                {analysis.classification_evidence && <div><dt className="font-semibold">Evidências</dt><dd className="break-words">{label(analysis.classification_evidence)}</dd></div>}
                {analysis.extracted_metadata && <div><dt className="font-semibold">Metadados extraídos</dt>
                  <dd><pre className="overflow-x-auto whitespace-pre-wrap break-words text-xs">{JSON.stringify(analysis.extracted_metadata, null, 2)}</pre></dd></div>}
              </dl>
            </section>
          )}
        </>
      )}
    </section>
  );
}
