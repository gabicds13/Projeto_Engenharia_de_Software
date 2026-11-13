import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NotificationsPage } from "./NotificationsPage";

const mocks = vi.hoisted(() => ({ refresh: vi.fn() }));

vi.mock("./NotificationsContext", () => ({
  useNotifications: () => ({
    items: [],
    available: false,
    actionError: null,
    markRead: vi.fn(),
    markAllRead: vi.fn(),
    refresh: mocks.refresh,
    wsOpen: false,
  }),
}));

describe("Etapa 4 — recuperação da central de notificações", () => {
  beforeEach(() => vi.clearAllMocks());

  it("mantém botão de reconexão quando as notificações falham", () => {
    mocks.refresh.mockResolvedValue(undefined);
    render(<NotificationsPage />);
    expect(screen.getByText("Notificações indisponível no momento")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(mocks.refresh).toHaveBeenCalledTimes(1);
  });
});
