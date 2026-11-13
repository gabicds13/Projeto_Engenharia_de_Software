import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../../lib/apiClient";
import type {
  DashboardCard,
  DashboardResponse,
  StoriesByStatus,
  WeeklyPoint,
} from "../../lib/types";
import { MetricCard, MetricNumber } from "./MetricCard";
import { WeeklyChart } from "./WeeklyChart";

interface Project {
  id?: string;
  project_id?: string;
  name?: string;
}

interface ProjectResponse {
  items?: Project[];
  projects?: Project[];
}

const CARD_LABELS: Record<string, string> = {
  commits_week: "Commits na semana",
  open_prs: "PRs abertos",
  reviews_pending: "Reviews pendentes",
  stories_by_status: "User Stories",
};

function normalizeProjects(
  response: Project[] | ProjectResponse,
): Project[] {
  if (Array.isArray(response)) {
    return response;
  }

  if (Array.isArray(response.items)) {
    return response.items;
  }

  if (Array.isArray(response.projects)) {
    return response.projects;
  }

  return [];
}

function getProjectId(project: Project): string {
  return project.project_id ?? project.id ?? "";
}

export function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [projectsLoading, setProjectsLoading] = useState(true);

  const [data, setData] = useState<DashboardResponse | null>(null);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  // Impede que a resposta atrasada de outro projeto apareça na tela atual.
  const activeProjectRef = useRef(projectId);
  activeProjectRef.current = projectId;

  const loadProjects = useCallback(async () => {
    setProjectsLoading(true);
    setProjectsError(null);

    try {
      const response = await api.get<Project[] | ProjectResponse>(
        "/api/bff/projects",
      );
      const list = normalizeProjects(response).filter((project) => getProjectId(project));

      setProjects(list);
      if (list.length > 0) {
        const next = list.some((project) => getProjectId(project) === activeProjectRef.current)
          ? activeProjectRef.current
          : getProjectId(list[0]);
        if (next !== activeProjectRef.current) {
          activeProjectRef.current = next;
          setData(null);
          setDashboardError(null);
          setProjectId(next);
        }
      } else {
        activeProjectRef.current = "";
        setProjectId("");
        setData(null);
        setProjectsError("Nenhum projeto disponível para este usuário.");
      }
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        // Em revogação de acesso, não preservar projetos e métricas carregados.
        activeProjectRef.current = "";
        setProjectId("");
        setProjects([]);
        setData(null);
      }
      setProjectsError(
        err instanceof ApiError && err.status === 403
          ? "Você não tem permissão para consultar os projetos."
          : "Não foi possível consultar os projetos no Módulo 1. As outras áreas do portal continuam disponíveis.",
      );
    } finally {
      setProjectsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  const loadDashboard = useCallback(async () => {
    if (!projectId) return;

    const requestedProjectId = projectId;
    try {
      const response = await api.get<DashboardResponse>(
        `/api/bff/dashboard?project_id=${encodeURIComponent(requestedProjectId)}`,
      );
      if (activeProjectRef.current !== requestedProjectId) return;

      setData(response);
      setDashboardError(null);
    } catch (err) {
      if (activeProjectRef.current !== requestedProjectId) return;

      // Se o acesso foi revogado, nunca exibir dados anteriormente carregados.
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setData(null);
        setDashboardError("Não foi possível validar seu acesso a este projeto.");
        return;
      }

      setDashboardError(
        "Não foi possível atualizar as métricas agora. Tente novamente.",
      );
      // Em falhas temporárias, mantemos o último resultado já exibido,
      // sem trocar o projeto nem conceder acesso adicional.
    }
  }, [projectId]);

  useEffect(() => {
    if (!projectId) {
      return;
    }

    void loadDashboard();

    const timer = setInterval(() => {
      void loadDashboard();
    }, 30_000);

    return () => clearInterval(timer);
  }, [loadDashboard, projectId]);

  if (projectsLoading) {
    return <p className="text-text-muted">Carregando projetos…</p>;
  }

  if (!projectId) {
    return (
      <section className="flex flex-col gap-4">
        <h1 className="text-xl font-semibold text-text">Dashboard do Projeto</h1>
        <p role="alert" className="rounded-lg border border-border bg-surface p-6 text-text-muted">
          {projectsError ?? "Nenhum projeto disponível para este usuário."}
        </p>
        {projectsError !== "Nenhum projeto disponível para este usuário." && (
          <button type="button" onClick={() => void loadProjects()}
            className="self-start rounded-md bg-primary px-4 py-2 text-sm font-medium text-white">
            Tentar novamente
          </button>
        )}
      </section>
    );
  }

  if (!data) {
    return (
      <section className="flex flex-col gap-4">
        <h1 className="text-xl font-semibold text-text">Dashboard do Projeto</h1>
        {dashboardError ? (
          <>
            <p role="alert" className="rounded-lg border border-border bg-surface p-6 text-text-muted">
              {dashboardError}
            </p>
            <button type="button" onClick={() => void loadDashboard()}
              className="self-start rounded-md bg-primary px-4 py-2 text-sm font-medium text-white">
              Tentar novamente
            </button>
          </>
        ) : (
          <p className="text-text-muted">Carregando métricas…</p>
        )}
      </section>
    );
  }

  const byKey = new Map(data.cards.map((card) => [card.key, card]));

  return (
    <section className="flex flex-col gap-6">
      {projectsError && (
        <div role="alert" className="rounded-lg border border-border bg-surface p-4 text-sm text-text-muted">
          {projectsError}
          <button type="button" onClick={() => void loadProjects()}
            className="ml-3 underline">
            Tentar novamente
          </button>
        </div>
      )}
      {dashboardError && (
        <div role="alert" className="rounded-lg border border-border bg-surface p-4 text-sm text-text-muted">
          {dashboardError} Exibindo os últimos dados carregados.
          <button type="button" onClick={() => void loadDashboard()}
            className="ml-3 underline">
            Tentar novamente
          </button>
        </div>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-text">
          Dashboard do Projeto
        </h1>

        {projects.length > 0 && (
          <select
            value={projectId}
            onChange={(event) => {
              activeProjectRef.current = event.target.value;
              setData(null);
              setDashboardError(null);
              setProjectId(event.target.value);
            }}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text"
          >
            {projects.map((project) => {
              const id = getProjectId(project);

              return (
                <option key={id} value={id}>
                  {project.name ?? id}
                </option>
              );
            })}
          </select>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SimpleMetric
          card={byKey.get("commits_week")}
          label={CARD_LABELS.commits_week}
        />

        <SimpleMetric
          card={byKey.get("open_prs")}
          label={CARD_LABELS.open_prs}
        />

        <SimpleMetric
          card={byKey.get("reviews_pending")}
          label={CARD_LABELS.reviews_pending}
        />

        <StoriesMetric card={byKey.get("stories_by_status")} />
      </div>

      <div className="rounded-lg border border-border bg-surface p-4">
        <h2 className="mb-3 text-lg font-semibold text-text">
          PRs e commits por semana
        </h2>

        {data.weekly.state === "unavailable" ? (
          <p className="text-sm text-text-muted">
            Gráfico indisponível no momento.
          </p>
        ) : (
          <WeeklyChart
            points={(data.weekly.value as { points: WeeklyPoint[] }).points}
          />
        )}
      </div>
    </section>
  );
}

function SimpleMetric({
  card,
  label,
}: {
  card?: DashboardCard;
  label: string;
}) {
  if (!card) {
    return <MetricCard label={label} state="unavailable" />;
  }

  return (
    <MetricCard label={label} state={card.state} stale={card.stale}>
      <MetricNumber value={Number(card.value ?? 0)} />
    </MetricCard>
  );
}

function StoriesMetric({ card }: { card?: DashboardCard }) {
  if (!card || card.state === "unavailable") {
    return (
      <MetricCard
        label={CARD_LABELS.stories_by_status}
        state="unavailable"
      />
    );
  }

  const stories = card.value as StoriesByStatus;

  return (
    <MetricCard
      label={CARD_LABELS.stories_by_status}
      state="ok"
      stale={card.stale}
    >
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-text">
        <Stat label="A fazer" value={stories.todo} />
        <Stat label="Em and." value={stories.in_progress} />
        <Stat label="Revisão" value={stories.in_review} />
        <Stat label="Concl." value={stories.done} />
      </div>
    </MetricCard>
  );
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <span className="flex items-baseline gap-1">
      <span className="metric text-md font-semibold text-text">
        {value}
      </span>

      <span className="text-xs text-text-muted">
        {label}
      </span>
    </span>
  );
}