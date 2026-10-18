import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useAuth } from "../../auth/AuthContext";
import { useWebSocket } from "../../hooks/useWebSocket";
import { api, getToken } from "../../lib/apiClient";
import { wsUrl } from "../../lib/config";
import type {
  ListResult,
  Notification,
  UnreadResult,
} from "../../lib/types";

interface NotificationsState {
  items: Notification[];
  unreadTotal: number;
  available: boolean;
  wsOpen: boolean;
  toasts: Notification[];
  refresh: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
  dismissToast: (id: string) => void;
}

const Ctx = createContext<NotificationsState | null>(null);

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [items, setItems] = useState<Notification[]>([]);
  const [unreadTotal, setUnreadTotal] = useState(0);
  const [available, setAvailable] = useState(true);
  const [toasts, setToasts] = useState<Notification[]>([]);
  const seen = useRef<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    if (!user) return;
    try {
      const list = await api.get<ListResult>("/api/bff/notifications");
      if (list.state === "unavailable" || !list.page) {
        setAvailable(false);
        return;
      }
      setAvailable(true);
      setItems(list.page.items);
      list.page.items.forEach((n) => seen.current.add(n.id));
      const unread = await api.get<UnreadResult>(
        "/api/bff/notifications/unread-count",
      );
      setUnreadTotal(unread.state === "ok" ? unread.count?.total ?? 0 : 0);
    } catch {
      setAvailable(false);
    }
  }, [user]);

  const markRead = useCallback(
    async (id: string) => {
      await api.patch(`/api/bff/notifications/${id}`);
      await refresh();
    },
    [refresh],
  );

  const markAllRead = useCallback(async () => {
    await api.post("/api/bff/notifications/read-all");
    await refresh();
  }, [refresh]);

  const dismissToast = useCallback(
    (id: string) => setToasts((t) => t.filter((n) => n.id !== id)),
    [],
  );

  const onMessage = useCallback((data: unknown) => {
    const msg = data as { event?: string; data?: Notification };
    if (msg.event === "notification.new" && msg.data) {
      const n = msg.data;
      if (seen.current.has(n.id)) return;
      seen.current.add(n.id);
      setItems((prev) => [n, ...prev]);
      setUnreadTotal((c) => c + 1);
      setToasts((prev) => [n, ...prev].slice(0, 4));
    }
  }, []);

  const socketUrl =
    user && getToken() ? wsUrl(`/ws/notifications?token=${getToken()}`) : null;
  const status = useWebSocket(socketUrl, { onMessage, onReconnect: refresh, enabled: !!user });

  useEffect(() => {
    if (user) void refresh();
  }, [user, refresh]);

  const value = useMemo<NotificationsState>(
    () => ({
      items,
      unreadTotal,
      available,
      wsOpen: status === "open",
      toasts,
      refresh,
      markRead,
      markAllRead,
      dismissToast,
    }),
    [items, unreadTotal, available, status, toasts, refresh, markRead, markAllRead, dismissToast],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useNotifications(): NotificationsState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useNotifications requer NotificationsProvider");
  return ctx;
}
