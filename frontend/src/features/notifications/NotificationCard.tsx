import type { Notification } from "../../lib/types";
import {
  priorityBadge,
  priorityBorder,
  priorityLabel,
  relativeTime,
  sourceMeta,
} from "./meta";

interface Props {
  notification: Notification;
  onMarkRead?: (id: string) => void;
}

export function NotificationCard({ notification, onMarkRead }: Props) {
  const { priority, source, title, body, created_at, read_at, id } = notification;
  const src = sourceMeta[source];

  return (
    <article
      data-testid="notification-card"
      data-priority={priority}
      className={`flex flex-col gap-1 rounded-lg border border-border border-l-4 ${priorityBorder[priority]} bg-surface p-4 ${
        read_at ? "opacity-70" : ""
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={`rounded px-2 py-0.5 text-xs font-semibold ${priorityBadge[priority]}`}
          >
            {priorityLabel[priority]}
          </span>
          <span className="text-xs text-text-muted">
            <span aria-hidden>{src.icon}</span> {src.label}
          </span>
        </div>
        <time className="text-xs text-text-muted" dateTime={created_at}>
          {relativeTime(created_at)}
        </time>
      </div>

      <h3 className="text-md font-semibold text-text">{title}</h3>
      <p className="text-sm text-text-muted">{body}</p>

      <div className="mt-1 flex items-center justify-between">
        <span className="text-xs text-text-muted" title={notification.reason}>
          {notification.classified_by === "llm" ? "Priorizado por IA" : "Priorizado por regras"}
        </span>
        {!read_at && onMarkRead && (
          <button
            type="button"
            onClick={() => onMarkRead(id)}
            className="text-sm font-medium text-primary hover:text-primary-hover"
          >
            Marcar como lida
          </button>
        )}
      </div>
    </article>
  );
}
