import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CodeReviewMetricsPanel } from "./CodeReviewMetricsPanel";

const getMock = vi.fn();
vi.mock("../../lib/apiClient", () => ({
  api: { get: (...args: unknown[]) => getMock(...args) },
}));

const sample = {
  project_id: "proj-1", dias: 14, source: "module-4", data_origin: "real",
  metrics: {
    total_revisoes: 3, total_achados: 7,
    por_prioridade: { critical: 1, high: 2, medium: 3, low: 1 },
    por_categoria: { Segurança: 2, Qualidade: 5 },
    por_arquitetura: { Microsserviços: 3 },
    revisoes_por_dia: [{ data: "2026-11-26", revisoes: 3, achados: 7 }],
  },
};

describe("Métricas reais do Módulo 4", () => {
  beforeEach(() => getMock.mockReset());

  it("mostra KPIs e os quatro gráficos da API por projeto", async () => {
    getMock.mockResolvedValue(sample);
    render(<CodeReviewMetricsPanel projectId="proj-1" />);
    expect(await screen.findByText("Revisões realizadas")).toBeInTheDocument();
    const panel = screen.getByRole("region", { name: "Métricas de Code Review - Módulo 4" });
    expect(within(panel).getByText("Total de achados")).toBeInTheDocument();
    expect(within(panel).getAllByRole("figure")).toHaveLength(4);
    expect(within(panel).getByText("Microsserviços")).toBeInTheDocument();
    expect(within(panel).getByText("Segurança")).toBeInTheDocument();
    expect(getMock).toHaveBeenCalledWith("/api/bff/code-reviews/metrics?project_id=proj-1&dias=14");
  });

  it("atualiza o período e oculta o resultado anterior", async () => {
    getMock.mockResolvedValueOnce(sample).mockResolvedValueOnce({ ...sample, dias: 30 });
    render(<CodeReviewMetricsPanel projectId="proj-1" />);
    expect(await screen.findByText("Revisões realizadas")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox", { name: "Período" }), { target: { value: "30" } });
    await waitFor(() => expect(getMock).toHaveBeenCalledWith("/api/bff/code-reviews/metrics?project_id=proj-1&dias=30"));
    expect(await screen.findByText("Revisões realizadas")).toBeInTheDocument();
  });

  it("não mostra dados de outro projeto nem dados simulados", async () => {
    getMock.mockResolvedValueOnce({ ...sample, project_id: "outro" });
    const { rerender } = render(<CodeReviewMetricsPanel projectId="proj-1" />);
    expect(await screen.findByRole("status")).toHaveTextContent("indisponíveis");
    expect(screen.queryByText("Revisões realizadas")).not.toBeInTheDocument();
    getMock.mockResolvedValueOnce({ ...sample, project_id: "proj-2", data_origin: "mock" });
    rerender(<CodeReviewMetricsPanel projectId="proj-2" />);
    expect(await screen.findByRole("status")).toHaveTextContent("indisponíveis");
    expect(screen.queryByText("Revisões realizadas")).not.toBeInTheDocument();
  });

  it("não mantém números antigos quando a atualização falha", async () => {
    getMock.mockResolvedValueOnce(sample).mockRejectedValueOnce(new Error("offline"));
    render(<CodeReviewMetricsPanel projectId="proj-1" />);
    expect(await screen.findByText("Revisões realizadas")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Atualizar métricas" }));
    expect(await screen.findByRole("status")).toHaveTextContent("indisponíveis");
    expect(screen.queryByText("Revisões realizadas")).not.toBeInTheDocument();
  });
});
