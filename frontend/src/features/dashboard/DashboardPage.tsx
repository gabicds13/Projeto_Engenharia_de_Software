import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { api, ApiError } from "../../lib/apiClient";
import type { DashboardCard, DashboardResponse, StoriesByStatus, WeeklyPoint } from "../../lib/types";
import { MetricCard, MetricNumber } from "./MetricCard";
import { WeeklyChart } from "./WeeklyChart";

const CARD_LABELS: Record<string, string> = {
  commits_week: "Commits na semana",
  open_prs: "PRs abertos",
  reviews_pending: "Reviews pendentes",
  stories_by_status: "User Stories",
};

export function DashboardPage() {
  const { user } = useAuth();
  const projectId = user?.project_ids[0] ?? "";
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!projectId) return;
    setError(null);
    try {
      const resp = await api.get<DashboardResponse>(
        `/api/bff/dashboard?project_id=${encodeURIComponent(projectId)}`,
      );
      setData(resp);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Falha ao carregar o dashboard.");
    }
  }, [projectId]);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 30_000);
    return () => clearInterval(t);
  }, [load]);

  if (error) {
    return (
      <p className="rounded-lg border border-border bg-surface p-6 text-text-muted">
        {error}
      </p>
    );
  }
  if (!data) return <p className="text-text-muted">Carregando métricas…</p>;

  const byKey = new Map(data.cards.map((c) => [c.key, c]));

  return (
    <section className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-text">Dashboard do Projeto</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SimpleMetric card={byKey.get("commits_week")} label={CARD_LABELS.commits_week} />
        <SimpleMetric card={byKey.get("open_prs")} label={CARD_LABELS.open_prs} />
        <SimpleMetric card={byKey.get("reviews_pending")} label={CARD_LABELS.reviews_pending} />
        <StoriesMetric card={byKey.get("stories_by_status")} />
      </div>

      <div className="rounded-lg border border-border bg-surface p-4">
        <h2 className="mb-3 text-lg font-semibold text-text">PRs e commits por semana</h2>
        {data.weekly.state === "unavailable" ? (
          <p className="text-sm text-text-muted">Gráfico indisponível no momento.</p>
        ) : (
          <WeeklyChart points={(data.weekly.value as { points: WeeklyPoint[] }).points} />
        )}
      </div>
    </section>
  );
}

function SimpleMetric({ card, label }: { card?: DashboardCard; label: string }) {
  if (!card) return <MetricCard label={label} state="unavailable" />;
  return (
    <MetricCard label={label} state={card.state} stale={card.stale}>
      <MetricNumber value={Number(card.value ?? 0)} />
    </MetricCard>
  );
}

function StoriesMetric({ card }: { card?: DashboardCard }) {
  if (!card || card.state === "unavailable") {
    return <MetricCard label={CARD_LABELS.stories_by_status} state="unavailable" />;
  }
  const s = card.value as StoriesByStatus;
  return (
    <MetricCard label={CARD_LABELS.stories_by_status} state="ok" stale={card.stale}>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-text">
        <Stat label="A fazer" value={s.todo} />
        <Stat label="Em and." value={s.in_progress} />
        <Stat label="Revisão" value={s.in_review} />
        <Stat label="Concl." value={s.done} />
      </div>
    </MetricCard>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <span className="flex items-baseline gap-1">
      <span className="metric text-md font-semibold text-text">{value}</span>
      <span className="text-xs text-text-muted">{label}</span>
    </span>
  );
}
