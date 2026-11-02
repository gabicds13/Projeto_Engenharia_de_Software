import { useCallback, useEffect, useState } from "react";
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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadProjects = async () => {
      setProjectsLoading(true);
      setError(null);

      try {
        const response = await api.get<Project[] | ProjectResponse>(
          "/api/bff/projects",
        );

        const list = normalizeProjects(response);

        setProjects(list);

        if (list.length > 0) {
          setProjectId(getProjectId(list[0]));
        } else {
          setError("Nenhum projeto disponível para este usuário.");
        }
      } catch (err) {
        setError(
          err instanceof ApiError
            ? err.message
            : "Não foi possível carregar os projetos.",
        );
      } finally {
        setProjectsLoading(false);
      }
    };

    void loadProjects();
  }, []);

  const loadDashboard = useCallback(async () => {
    if (!projectId) {
      return;
    }

    try {
      const response = await api.get<DashboardResponse>(
        `/api/bff/dashboard?project_id=${encodeURIComponent(projectId)}`,
      );

      setData(response);
      setError(null);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao carregar o dashboard.",
      );
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

  if (error) {
    return (
      <p className="rounded-lg border border-border bg-surface p-6 text-text-muted">
        {error}
      </p>
    );
  }

  if (!data) {
    return <p className="text-text-muted">Carregando métricas…</p>;
  }

  const byKey = new Map(data.cards.map((card) => [card.key, card]));

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-text">
          Dashboard do Projeto
        </h1>

        {projects.length > 0 && (
          <select
            value={projectId}
            onChange={(event) => {
              setData(null);
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