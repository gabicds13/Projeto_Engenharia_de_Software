import { useMemo, useState } from "react";
import { UnavailableState } from "../../components/UnavailableState";
import type { Priority, Source } from "../../lib/types";
import { NotificationCard } from "./NotificationCard";
import { useNotifications } from "./NotificationsContext";
import { priorityLabel, sourceMeta } from "./meta";

type StatusFilter = "all" | "unread" | "read";

export function NotificationsPage() {
  const { items, available, markRead, markAllRead, wsOpen } = useNotifications();
  const [priority, setPriority] = useState<Priority | "all">("all");
  const [source, setSource] = useState<Source | "all">("all");
  const [status, setStatus] = useState<StatusFilter>("all");

  const filtered = useMemo(
    () =>
      items.filter((n) => {
        if (priority !== "all" && n.priority !== priority) return false;
        if (source !== "all" && n.source !== source) return false;
        if (status === "unread" && n.read_at) return false;
        if (status === "read" && !n.read_at) return false;
        return true;
      }),
    [items, priority, source, status],
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
        <button
          type="button"
          onClick={() => void markAllRead()}
          className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
        >
          Marcar todas como lidas
        </button>
      </div>

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
      </div>

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
