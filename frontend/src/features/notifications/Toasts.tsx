import { useNotifications } from "./NotificationsContext";
import { priorityBorder, priorityBadge, priorityLabel, sourceMeta } from "./meta";

// Toasts de novas notificações (canto inferior direito).
export function Toasts() {
  const { toasts, dismissToast } = useNotifications();
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2">
      {toasts.map((n) => (
        <div
          key={n.id}
          role="alert"
          className={`pointer-events-auto rounded-lg border border-border border-l-4 ${priorityBorder[n.priority]} bg-surface p-3 shadow-lg`}
        >
          <div className="flex items-center justify-between">
            <span
              className={`rounded px-2 py-0.5 text-xs font-semibold ${priorityBadge[n.priority]}`}
            >
              {priorityLabel[n.priority]}
            </span>
            <button
              type="button"
              onClick={() => dismissToast(n.id)}
              className="text-sm text-text-muted hover:text-text"
              aria-label="Dispensar"
            >
              ✕
            </button>
          </div>
          <p className="mt-1 text-xs text-text-muted">{sourceMeta[n.source].label}</p>
          <p className="text-sm font-semibold text-text">{n.title}</p>
        </div>
      ))}
    </div>
  );
}
