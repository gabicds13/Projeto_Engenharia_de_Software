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
  actionError: string | null;
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
  const [actionError, setActionError] = useState<string | null>(null);
  const refreshRequest = useRef(0);
  const pendingReads = useRef<Set<string>>(new Set());
  const pendingReadAll = useRef(false);
  const seen = useRef<Set<string>>(new Set());
  const hydrated = useRef(false);

  const refresh = useCallback(
    async (showRecoveredToasts = false) => {
      if (!user) return;
      const requestId = ++refreshRequest.current;

      try {
        const list = await api.get<ListResult>("/api/bff/notifications");
        if (requestId !== refreshRequest.current) return;

        if (list.state === "unavailable" || !list.page) {
          setAvailable(false);
          return;
        }

        const unseenItems = list.page.items.filter(
          (notification) => !seen.current.has(notification.id),
        );

        setAvailable(true);
        setItems(list.page.items);

        list.page.items.forEach((notification) => {
          seen.current.add(notification.id);
        });

        if (
          showRecoveredToasts &&
          hydrated.current &&
          unseenItems.length > 0
        ) {
          setToasts((previousToasts) => {
            const toastIds = new Set(
              previousToasts.map((toast) => toast.id),
            );

            const recoveredToasts = unseenItems.filter(
              (notification) => !toastIds.has(notification.id),
            );

            return [...recoveredToasts, ...previousToasts].slice(0, 4);
          });
        }

        const unread = await api.get<UnreadResult>(
          "/api/bff/notifications/unread-count",
        );
        if (requestId !== refreshRequest.current) return;

        setUnreadTotal(
          unread.state === "ok" ? unread.count?.total ?? 0 : 0,
        );

        hydrated.current = true;
      } catch {
        if (requestId === refreshRequest.current) {
          setAvailable(false);
        }
      }
    },
    [user],
  );

  const markRead = useCallback(
    async (id: string) => {
      if (pendingReads.current.has(id) || pendingReadAll.current) return;
      const unread = items.some((item) => item.id === id && !item.read_at);
      if (!unread) return;

      pendingReads.current.add(id);
      setActionError(null);
      try {
        await api.patch(`/api/bff/notifications/${id}`);

        // Atualiza a lista e o contador sem depender de um novo GET.
        // Invalida buscas antigas para não sobrescrever o estado recém-alterado.
        refreshRequest.current += 1;
        const readAt = new Date().toISOString();
        setItems((previous) =>
          previous.map((item) =>
            item.id === id ? { ...item, read_at: readAt } : item,
          ),
        );
        setUnreadTotal((previous) => Math.max(0, previous - 1));
      } catch {
        setActionError("Não foi possível marcar esta notificação como lida.");
      } finally {
        pendingReads.current.delete(id);
      }
    },
    [items],
  );

  const markAllRead = useCallback(async () => {
    if (pendingReadAll.current) return;
    pendingReadAll.current = true;
    setActionError(null);
    try {
      await api.post("/api/bff/notifications/read-all");

      refreshRequest.current += 1;
      const readAt = new Date().toISOString();
      setItems((previous) =>
        previous.map((item) => ({
          ...item,
          read_at: item.read_at ?? readAt,
        })),
      );
      setUnreadTotal(0);
    } catch {
      setActionError("Não foi possível marcar todas as notificações como lidas.");
    } finally {
      pendingReadAll.current = false;
    }
  }, []);

  const dismissToast = useCallback(
    (id: string) => setToasts((t) => t.filter((n) => n.id !== id)),
    [],
  );

  const onMessage = useCallback((data: unknown) => {
    const msg = data as { event?: string; data?: Notification };

    if (msg.event === "notification.new" && msg.data) {
      const n = msg.data;
      const alreadySeen = seen.current.has(n.id);

      if (!alreadySeen) {
        seen.current.add(n.id);
        setItems((prev) => [n, ...prev]);
        setUnreadTotal((c) => c + 1);
      }

      setToasts((prev) => {
        if (prev.some((toast) => toast.id === n.id)) {
          return prev;
        }

        return [n, ...prev].slice(0, 4);
      });
    }
  }, []);
  const token = user ? getToken() : null;

const socketUrl =
  user && token ? wsUrl("/ws/notifications") : null;

const status = useWebSocket(socketUrl, {
  onMessage,
  onReconnect: refresh,
  enabled: !!user,
  authToken: token ?? undefined,
});

  useEffect(() => {
    if (user) void refresh();
  }, [user, refresh]);

  const value = useMemo<NotificationsState>(
    () => ({
      items,
      unreadTotal,
      available,
      actionError,
      wsOpen: status === "open",
      toasts,
      refresh,
      markRead,
      markAllRead,
      dismissToast,
    }),
    [items, unreadTotal, available, actionError, status, toasts, refresh, markRead, markAllRead, dismissToast],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useNotifications(): NotificationsState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useNotifications requer NotificationsProvider");
  return ctx;
}
