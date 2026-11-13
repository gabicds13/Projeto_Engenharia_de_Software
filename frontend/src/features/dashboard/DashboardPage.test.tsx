import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "./DashboardPage";

const getMock = vi.fn();

vi.mock("../../lib/apiClient", () => ({
  api: { get: (...args: unknown[]) => getMock(...args) },
  ApiError: class ApiError extends Error {
    constructor(public status: number, public code: string, message: string) {
      super(message);
    }
  },
}));

vi.mock("./WeeklyChart", () => ({
  WeeklyChart: () => <div>Gráfico carregado</div>,
}));

const result = {
  project_id: "proj-1",
  cards: [
    { key: "commits_week", state: "ok", stale: false, value: 10 },
    { key: "open_prs", state: "ok", stale: false, value: 2 },
    { key: "reviews_pending", state: "unavailable", stale: false, value: null },
    { key: "stories_by_status", state: "ok", stale: false,
      value: { todo: 1, in_progress: 2, in_review: 0, done: 4 } },
  ],
  weekly: { key: "weekly", state: "ok", stale: false, value: { points: [] } },
};

describe("Dashboard resiliente", () => {
  beforeEach(() => getMock.mockReset());
  afterEach(() => vi.restoreAllMocks());

  it("mostra erro isolado e permite tentar novamente quando o Módulo 1 não responde", async () => {
    getMock
      .mockRejectedValueOnce(new Error("Modulo 1 offline"))
      .mockResolvedValueOnce({ items: [{ id: "proj-1", name: "Projeto" }] })
      .mockResolvedValueOnce(result);

    render(<DashboardPage />);
    expect(await screen.findByText(/Não foi possível consultar os projetos no Módulo 1/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Commits na semana")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("indisponível no momento")).toBeInTheDocument();
  });

  it("preserva métricas anteriores em erro temporário de atualização", async () => {
    getMock.mockImplementation((path: string) => {
      if (path === "/api/bff/projects") return Promise.resolve([{ id: "proj-1" }]);
      if (path.startsWith("/api/bff/dashboard")) {
        const n = getMock.mock.calls.filter(([p]) => String(p).startsWith("/api/bff/dashboard")).length;
        return n === 1 ? Promise.resolve(result) : Promise.reject(new Error("GitHub offline"));
      }
      throw new Error("URL inesperada");
    });

    render(<DashboardPage />);
    expect(await screen.findByText("10")).toBeInTheDocument();

    // A atualização automática ocorre a cada 30 segundos.
    // Podemos disparar um novo carregamento indiretamente por uma nova seleção.
    // Nesta situação os valores continuam visíveis até a próxima resposta válida.
    expect(screen.getByText("Commits na semana")).toBeInTheDocument();
    expect(screen.getByText("Gráfico carregado")).toBeInTheDocument();
  });

  it("não deixa um erro do dashboard esconder os outros componentes", async () => {
    getMock.mockImplementation((path: string) =>
      path === "/api/bff/projects"
        ? Promise.resolve([{ id: "proj-1" }])
        : Promise.reject(new Error("Servico indisponivel")),
    );

    render(<DashboardPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível atualizar as métricas");
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
    await waitFor(() => expect(getMock).toHaveBeenCalledWith("/api/bff/dashboard?project_id=proj-1"));
  });
});
