import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Notification } from "../../lib/types";
import { NotificationsProvider, useNotifications } from "./NotificationsContext";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
}));

vi.mock("../../auth/AuthContext", () => ({
  useAuth: () => ({ user: { user_id: "user-1", project_ids: ["proj-123"] } }),
}));
vi.mock("../../hooks/useWebSocket", () => ({
  useWebSocket: () => "open",
}));
vi.mock("../../lib/apiClient", () => ({
  api: mocks,
  getToken: () => "test-token",
}));
vi.mock("../../lib/config", () => ({
  wsUrl: (path: string) => path,
}));

const notifications: Notification[] = [
  {
    id: "ntf-1",
    source: "chat",
    type: "chat.mention",
    priority: "medium",
    relevance_score: 0.7,
    reason: "Menção",
    classified_by: "rules",
    project_id: "proj-123",
    title: "Primeira notificação",
    body: "Você foi mencionado",
    link: "/chat",
    created_at: "2026-11-12T12:00:00Z",
    read_at: null,
  },
  {
    id: "ntf-2",
    source: "github",
    type: "github.pr.comment",
    priority: "low",
    relevance_score: 0.3,
    reason: "Comentário",
    classified_by: "rules",
    project_id: "proj-123",
    title: "Segunda notificação",
    body: "Comentário novo",
    link: null,
    created_at: "2026-11-12T12:01:00Z",
    read_at: null,
  },
];

function Controls() {
  const { items, unreadTotal, markRead, markAllRead, actionError } = useNotifications();
  return (
    <div>
      <span data-testid="unread">{unreadTotal}</span>
      <span data-testid="first-read">{items[0]?.read_at ? "sim" : "não"}</span>
      <button onClick={() => void markRead("ntf-1")}>Marcar primeira</button>
      <button onClick={() => void markAllRead()}>Marcar todas</button>
      {actionError && <div role="alert">{actionError}</div>}
    </div>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.get.mockImplementation((path: string) => {
    if (path === "/api/bff/notifications") {
      return Promise.resolve({
        state: "ok",
        page: { items: notifications, next_cursor: null },
      });
    }
    if (path === "/api/bff/notifications/unread-count") {
      return Promise.resolve({ state: "ok", count: { total: 2 } });
    }
    throw new Error(`Unexpected GET: ${path}`);
  });
  mocks.patch.mockResolvedValue({ status: "ok" });
  mocks.post.mockResolvedValue({ status: "ok" });
});

describe("NotificationsProvider", () => {
  it("atualiza notificação e contador sem recarregar a página", async () => {
    render(
      <NotificationsProvider>
        <Controls />
      </NotificationsProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("unread").textContent).toBe("2"));
    fireEvent.click(screen.getByText("Marcar primeira"));
    await waitFor(() => {
      expect(screen.getByTestId("unread").textContent).toBe("1");
      expect(screen.getByTestId("first-read").textContent).toBe("sim");
    });
    expect(mocks.patch).toHaveBeenCalledWith("/api/bff/notifications/ntf-1");
  });

  it("zera o contador ao marcar todas como lidas", async () => {
    render(
      <NotificationsProvider>
        <Controls />
      </NotificationsProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("unread").textContent).toBe("2"));
    fireEvent.click(screen.getByText("Marcar todas"));
    await waitFor(() => {
      expect(screen.getByTestId("unread").textContent).toBe("0");
      expect(screen.getByTestId("first-read").textContent).toBe("sim");
    });
  });

  it("mantém a notificação não lida e mostra erro se a API falhar", async () => {
    mocks.patch.mockRejectedValueOnce(new Error("indisponível"));
    render(
      <NotificationsProvider>
        <Controls />
      </NotificationsProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("unread").textContent).toBe("2"));
    fireEvent.click(screen.getByText("Marcar primeira"));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível marcar"),
    );
    expect(screen.getByTestId("unread").textContent).toBe("2");
    expect(screen.getByTestId("first-read").textContent).toBe("não");
  });
});
