import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChatPage } from "./ChatPage";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("../../auth/AuthContext", () => ({
  useAuth: () => ({ user: { user_id: "alice" } }),
}));
vi.mock("../../hooks/useWebSocket", () => ({
  useWebSocket: () => "open",
}));
vi.mock("../../lib/apiClient", () => ({
  api: mocks,
  getToken: () => "test-token",
  ApiError: class ApiError extends Error {
    constructor(public status: number, public code: string, message: string) {
      super(message);
    }
  },
}));
vi.mock("../../lib/config", () => ({
  wsUrl: (path: string) => path,
}));
vi.mock("./DirectChatPanel", () => ({
  DirectChatPanel: () => <div>Conversas privadas disponíveis</div>,
}));

beforeEach(() => {
  // jsdom não implementa o scroll nativo do navegador.
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
    configurable: true,
    value: vi.fn(),
  });
  vi.clearAllMocks();
  mocks.get.mockImplementation((path: string) => {
    if (path === "/api/bff/projects") {
      return Promise.resolve([{ id: "proj-1", name: "Projeto um" }]);
    }
    if (path.endsWith("/unread")) {
      return Promise.resolve({ project_id: "proj-1", unread: 0 });
    }
    if (path.endsWith("/messages")) {
      return Promise.resolve({
        state: "ok",
        stale: false,
        project_id: "proj-1",
        messages: [],
      });
    }
    throw new Error(`GET inesperado: ${path}`);
  });
  mocks.post.mockResolvedValue(undefined);
});

describe("Etapa 4 — revisão do Chat", () => {
  it("preserva o texto e informa o erro quando o envio falha", async () => {
    mocks.post.mockImplementation((path: string) => {
      if (path.endsWith("/messages")) return Promise.reject(new Error("Chat temporariamente offline"));
      return Promise.resolve(undefined);
    });

    render(<ChatPage />);
    const field = await screen.findByPlaceholderText("Escreva uma mensagem…");
    fireEvent.change(field, { target: { value: "Mensagem para tentar novamente" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível enviar");
    expect(field).toHaveValue("Mensagem para tentar novamente");
    expect(screen.getByRole("button", { name: "Enviar" })).toBeEnabled();
  });

  it("deixa as conversas privadas acessíveis quando o chat geral falha", async () => {
    mocks.get.mockImplementation((path: string) => {
      if (path === "/api/bff/projects") return Promise.resolve([{ id: "proj-1" }]);
      if (path.endsWith("/unread")) return Promise.resolve({ unread: 0 });
      if (path.endsWith("/messages")) return Promise.resolve({ state: "unavailable", messages: [] });
      throw new Error(`GET inesperado: ${path}`);
    });

    render(<ChatPage />);
    expect(await screen.findByText("Chat geral indisponível no momento")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Conversas privadas" }));
    expect(await screen.findByText("Conversas privadas disponíveis")).toBeInTheDocument();
  });

  it("permite recuperar o chat geral pelo botão tentar novamente", async () => {
    let calls = 0;
    mocks.get.mockImplementation((path: string) => {
      if (path === "/api/bff/projects") return Promise.resolve([{ id: "proj-1" }]);
      if (path.endsWith("/unread")) return Promise.resolve({ unread: 0 });
      if (path.endsWith("/messages")) {
        calls += 1;
        return Promise.resolve(calls === 1
          ? { state: "unavailable", messages: [] }
          : { state: "ok", messages: [], project_id: "proj-1", stale: false });
      }
      throw new Error(`GET inesperado: ${path}`);
    });

    render(<ChatPage />);
    const retry = await screen.findByRole("button", { name: "Tentar novamente" });
    fireEvent.click(retry);
    await waitFor(() =>
      expect(screen.getByPlaceholderText("Escreva uma mensagem…")).toBeInTheDocument(),
    );
  });
});
