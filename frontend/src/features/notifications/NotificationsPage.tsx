import { useMemo, useState } from "react";
import { UnavailableState } from "../../components/UnavailableState";
import type { Notification, Priority, Source } from "../../lib/types";
import { NotificationCard } from "./NotificationCard";
import { useNotifications } from "./NotificationsContext";
import { priorityLabel, sourceMeta } from "./meta";

type StatusFilter = "all" | "unread" | "read";
type SortOrder = "relevance" | "recent";
const priorityRank: Record<Priority, number> = { critical: 3, high: 2, medium: 1, low: 0 };

// Exemplo exclusivamente visual. Não é enviado à API nem salvo no Neon.
const demoNotification: Notification = {
  id: "demo-ia-local",
  source: "github",
  type: "pull_request.opened",
  project_id: "projeto-ficticio",
  priority: "high",
  relevance_score: 0.87,
  reason: "Alteração técnica importante aguardando revisão.",
  classified_by: "llm",
  title: "Exemplo: pull request aguardando revisão",
  body: "Um pull request fictício alterou testes do backend.",
  summary: "Mudança no backend precisa de revisão técnica.",
  group_key: "code-review",
  created_at: new Date().toISOString(),
  read_at: null,
  link: null,
};

export function NotificationsPage() {
  const { items, available, actionError, markRead, markAllRead, wsOpen } = useNotifications();
  const [priority, setPriority] = useState<Priority | "all">("all");
  const [source, setSource] = useState<Source | "all">("all");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [sortOrder, setSortOrder] = useState<SortOrder>("relevance");
  const [onlyRelevant, setOnlyRelevant] = useState(false);
  const [showDemo, setShowDemo] = useState(false);

  const filtered = useMemo(
    () =>
      items.filter((n) => {
        if (priority !== "all" && n.priority !== priority) return false;
        if (source !== "all" && n.source !== source) return false;
        if (status === "unread" && n.read_at) return false;
        if (status === "read" && !n.read_at) return false;
        if (onlyRelevant && n.priority !== "critical" && (n.personal_relevance_score ?? n.relevance_score) < 0.65) return false;
        return true;
      }).sort((a, b) => {
        const dateDiff = new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        if (sortOrder === "recent") return dateDiff;
        const priorityDiff = priorityRank[b.priority] - priorityRank[a.priority];
        if (priorityDiff !== 0) return priorityDiff;
        const scoreDiff = (b.personal_relevance_score ?? b.relevance_score) - (a.personal_relevance_score ?? a.relevance_score);
        return scoreDiff || dateDiff;
      }),
    [items, priority, source, status, sortOrder, onlyRelevant],
  );

  if (!available) return <UnavailableState label="Notificações" />;

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-semibold text-text">Notificações</h1>
          <span
            className={`h-2 w-2 rounded-full ${wsOpen ? "bg-success" : "bg-priority-low"}`}
            title={wsOpen ? "Tempo real conectado" : "Reconectando…"}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {import.meta.env.DEV && (
            <button
              type="button"
              aria-pressed={showDemo}
              onClick={() => setShowDemo((current) => !current)}
              className="rounded-md border border-border bg-surface px-3 py-2 text-sm font-medium text-text hover:bg-bg"
            >
              {showDemo ? "Ocultar exemplo local" : "Ver exemplo de IA (local)"}
            </button>
          )}
          <button
            type="button"
            onClick={() => void markAllRead()}
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Marcar todas como lidas
          </button>
        </div>
      </div>

      {actionError && (
        <p role="alert" className="rounded-md border border-priority-critical/40 bg-priority-critical/10 p-3 text-sm text-text">
          {actionError}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <Select value={priority} onChange={(v) => setPriority(v as Priority | "all")}>
          <option value="all">Todas as prioridades</option>
          {(["critical", "high", "medium", "low"] as Priority[]).map((p) => (
            <option key={p} value={p}>
              {priorityLabel[p]}
            </option>
          ))}
        </Select>
        <Select value={source} onChange={(v) => setSource(v as Source | "all")}>
          <option value="all">Todas as origens</option>
          {(Object.keys(sourceMeta) as Source[]).map((s) => (
            <option key={s} value={s}>
              {sourceMeta[s].label}
            </option>
          ))}
        </Select>
        <Select value={status} onChange={(v) => setStatus(v as StatusFilter)}>
          <option value="all">Todas</option>
          <option value="unread">Não lidas</option>
          <option value="read">Lidas</option>
        </Select>
        <Select value={sortOrder} onChange={(v) => setSortOrder(v as SortOrder)}>
          <option value="relevance">Mais relevantes primeiro</option>
          <option value="recent">Mais recentes primeiro</option>
        </Select>
        <label className="flex items-center gap-2 text-sm text-text-muted">
          <input
            type="checkbox"
            checked={onlyRelevant}
            onChange={(e) => setOnlyRelevant(e.target.checked)}
          />
          Mostrar apenas relevantes
        </label>
      </div>

      {import.meta.env.DEV && showDemo && (
        <aside aria-label="Exemplo fictício de classificação por IA" className="flex flex-col gap-2">
          <p className="rounded-md border border-border bg-surface px-3 py-2 text-sm text-text">
            <strong>EXEMPLO LOCAL — resposta de IA simulada.</strong>{" "}
            Nenhuma notificação foi enviada ao Gemini ou salva no Neon.
            Este exemplo não altera a contagem de não lidas.
          </p>
          <NotificationCard notification={demoNotification} />
        </aside>
      )}

      {filtered.length === 0 ? (
        <p className="rounded-lg border border-border bg-surface p-6 text-center text-text-muted">
          Nenhuma notificação para os filtros atuais.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((n) => (
            <NotificationCard key={n.id} notification={n} onMarkRead={markRead} />
          ))}
        </div>
      )}
    </section>
  );
}

function Select({
  value,
  onChange,
  children,
}: {
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md border border-border bg-surface px-3 py-2 text-sm text-text"
    >
      {children}
    </select>
  );
}
