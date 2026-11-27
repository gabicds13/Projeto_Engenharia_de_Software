import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ArtifactsPage } from "./ArtifactsPage";

const getMock = vi.fn();
const downloadMock = vi.fn();
vi.mock("../../lib/apiClient", () => ({
  api: { get: (...args: unknown[]) => getMock(...args) },
  downloadBffFile: (...args: unknown[]) => downloadMock(...args),
  ApiError: class ApiError extends Error {
    constructor(public status: number, public code: string, message: string) {
      super(message);
    }
  },
}));

describe("Módulo 3 — artefatos", () => {
  beforeEach(() => { getMock.mockReset(); downloadMock.mockReset(); });

  it("mostra projetos autorizados, artefatos e filtros GET", async () => {
    getMock.mockImplementation((path: string) => {
      if (path === "/api/bff/module3/projects") return Promise.resolve([{ id: "p-123", name: "Projeto" }]);
      if (path.includes("/artifacts")) return Promise.resolve({ items: [{ id: "a-1", name: "Requisitos", artifact_type: "PDF" }] });
      throw new Error("Endpoint inesperado " + path);
    });
    render(<ArtifactsPage />);
    expect(await screen.findByText("Requisitos")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Nome do documento"), { target: { value: "Requ" } });
    fireEvent.change(screen.getByLabelText("Tipo de arquivo"), { target: { value: "PDF" } });
    fireEvent.click(screen.getByRole("button", { name: "Buscar" }));
    await waitFor(() => expect(getMock).toHaveBeenCalledWith("/api/bff/module3/projects/p-123/artifacts?search=Requ&artifact_type=PDF"));
    expect(screen.getByRole("link", { name: "Abrir Módulo 3" })).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("consulta apenas uma análise existente informada pela versão", async () => {
    getMock.mockImplementation((path: string) => {
      if (path === "/api/bff/module3/projects") return Promise.resolve([{ id: "p-123" }]);
      if (path.endsWith("/artifacts")) return Promise.resolve([{ id: "a-1", project_id: "p-123", name: "Projeto.pdf" }]);
      if (path.endsWith("/versions")) return Promise.resolve({ versions: [{ id: "v-1", artifact_id: "a-1", project_id: "p-123", analysis_id: "an-2" }] });
      if (path.endsWith("/analyses/an-2")) return Promise.resolve({
        status: "COMPLETED", classification: "architecture_document",
        summary: "Arquitetura em microsserviços", confidence: 0.9,
      });
      throw new Error("Endpoint inesperado " + path);
    });
    render(<ArtifactsPage />);
    expect(await screen.findByText("Projeto.pdf")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ver versões" }));
    fireEvent.click(await screen.findByRole("button", { name: "Ver análise existente" }));
    expect(await screen.findByText("Arquitetura em microsserviços")).toBeInTheDocument();
    expect(screen.getByText("90.0%")).toBeInTheDocument();
    expect(getMock).toHaveBeenCalledWith("/api/bff/module3/projects/p-123/artifacts/a-1/analyses/an-2");
  });

  it("não oculta o restante do portal quando Módulo 3 falha", async () => {
    getMock.mockRejectedValue(new Error("Upstream 503"));
    render(<ArtifactsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível interpretar os projetos retornados");
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

  it("mostra a causa segura devolvida pelo BFF quando o Módulo 1 não responde", async () => {
    const { ApiError } = await import("../../lib/apiClient");
    getMock.mockRejectedValue(new ApiError(503, "service_unavailable", "Não foi possível consultar os projetos do usuário."));
    render(<ArtifactsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("HTTP 503");
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível consultar os projetos do usuário.");
  });

  it("avisa quando não existem projetos associados", async () => {
    getMock.mockResolvedValue({ items: [] });
    render(<ArtifactsPage />);
    expect(await screen.findByText(/Nenhum projeto do Módulo 3 está associado/)).toBeInTheDocument();
  });
});
