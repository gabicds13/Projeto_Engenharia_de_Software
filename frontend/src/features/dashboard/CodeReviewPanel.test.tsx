import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CodeReviewPanel } from "./CodeReviewPanel";

const getMock = vi.fn();

vi.mock("../../lib/apiClient", () => ({
  api: { get: (...args: unknown[]) => getMock(...args) },
}));

const sample = {
  project_id: "proj-1",
  source: "module-4",
  history_limited: true,
  pending_reviews: null,
  items: [
    {
      id: "review-123",
      reviewed_at: "2026-11-15T12:00:00+00:00",
      pr_url: "https://github.com/equipe/repo/pull/3",
      architecture: "multicamadas",
      findings_count: 2,
      severity_counts: { Alta: 1, "Média": 1 },
    },
  ],
};

describe("Painel de revisões do Módulo 4", () => {
  beforeEach(() => getMock.mockReset());

  it("exibe somente metadados reais e informa limitação de histórico", async () => {
    getMock.mockResolvedValue(sample);
    render(<CodeReviewPanel projectId="proj-1" />);

    const panel = await screen.findByRole("region", {
      name: "Revisões de código - Módulo 4",
    });
    expect(panel).toHaveTextContent("2 achados");
    expect(panel).toHaveTextContent("entre as 20 análises mais recentes");
    expect(panel).toHaveTextContent("Alta: 1");
    expect(screen.getByRole("link", { name: "Ver Pull Request no GitHub" }))
      .toHaveAttribute("href", "https://github.com/equipe/repo/pull/3");
    expect(getMock).toHaveBeenCalledWith("/api/bff/code-reviews?project_id=proj-1");
  });

  it("mantém as métricas isoladas quando o M4 está indisponível", async () => {
    getMock.mockRejectedValue(new Error("offline"));
    render(<CodeReviewPanel projectId="proj-1" />);
    expect(await screen.findByRole("status"))
      .toHaveTextContent("Histórico de revisões indisponível");
  });

  it("não exibe dados retornados para outro projeto", async () => {
    getMock.mockResolvedValue({ ...sample, project_id: "projeto-errado" });
    render(<CodeReviewPanel projectId="proj-1" />);
    expect(await screen.findByRole("status"))
      .toHaveTextContent("Histórico de revisões indisponível");
    expect(screen.queryByRole("link", { name: "Ver Pull Request no GitHub" }))
      .not.toBeInTheDocument();
  });

  it("não mantém revisões antigas após atualização falhar", async () => {
    getMock.mockResolvedValueOnce(sample).mockRejectedValueOnce(new Error("offline"));
    render(<CodeReviewPanel projectId="proj-1" />);
    expect(await screen.findByRole("link", { name: "Ver Pull Request no GitHub" }))
      .toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Atualizar revisões" }));
    await waitFor(() => expect(screen.getByRole("status"))
      .toHaveTextContent("Histórico de revisões indisponível"));
    expect(screen.queryByRole("link", { name: "Ver Pull Request no GitHub" }))
      .not.toBeInTheDocument();
  });

  it("mostra estado vazio sem apresentar zero reviews pendentes", async () => {
    getMock.mockResolvedValue({ ...sample, items: [] });
    render(<CodeReviewPanel projectId="proj-1" />);
    expect(await screen.findByText(/Nenhuma revisão deste projeto encontrada/))
      .toBeInTheDocument();
    expect(screen.getByText(/Não representa o total de revisões/)).toBeInTheDocument();
  });
});
