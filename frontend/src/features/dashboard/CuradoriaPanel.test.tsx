import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CuradoriaPanel } from "./CuradoriaPanel";

const getMock = vi.fn();

vi.mock("../../lib/apiClient", () => ({
  api: { get: (...args: unknown[]) => getMock(...args) },
}));

const feed = {
  source: "module-5",
  scope: "global",
  updated_at: "2026-11-15T12:00:00+00:00",
  articles: [{
    title: "Novidades do Python",
    url: "https://python.org/blog",
    source: "Python Insider",
    category: "Desenvolvimento",
    published_at: "2026-11-15",
  }],
};

describe("Tendências do Módulo 5", () => {
  beforeEach(() => getMock.mockReset());

  it("mostra título, fonte, categoria e link real", async () => {
    getMock.mockResolvedValue(feed);
    render(<CuradoriaPanel />);
    const panel = await screen.findByRole("region", {
      name: "Tendências tecnológicas - Módulo 5",
    });
    expect(panel).toHaveTextContent("Feed geral");
    expect(panel).toHaveTextContent("Python Insider");
    expect(screen.getByRole("link", { name: "Novidades do Python" }))
      .toHaveAttribute("href", "https://python.org/blog");
    expect(getMock).toHaveBeenCalledWith("/api/bff/curadoria/em-alta");
  });

  it("preserva o Dashboard quando o M5 está fora do ar", async () => {
    getMock.mockRejectedValueOnce(new Error("offline"));
    render(<CuradoriaPanel />);
    expect(await screen.findByRole("status"))
      .toHaveTextContent("Tendências indisponíveis");
  });

  it("não mostra artigos de uma resposta fora do contrato", async () => {
    getMock.mockResolvedValue({ ...feed, scope: "project" });
    render(<CuradoriaPanel />);
    expect(await screen.findByRole("status"))
      .toHaveTextContent("Tendências indisponíveis");
    expect(screen.queryByRole("link", { name: "Novidades do Python" }))
      .not.toBeInTheDocument();
  });

  it("apaga dados anteriores após atualização com falha", async () => {
    getMock.mockResolvedValueOnce(feed).mockRejectedValueOnce(new Error("offline"));
    render(<CuradoriaPanel />);
    expect(await screen.findByRole("link", { name: "Novidades do Python" }))
      .toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Atualizar tendências" }));
    await waitFor(() => expect(screen.getByRole("status"))
      .toHaveTextContent("Tendências indisponíveis"));
    expect(screen.queryByRole("link", { name: "Novidades do Python" }))
      .not.toBeInTheDocument();
  });

  it("mostra quando o feed está vazio", async () => {
    getMock.mockResolvedValue({ ...feed, articles: [] });
    render(<CuradoriaPanel />);
    expect(await screen.findByText("Nenhum artigo disponível no feed do Módulo 5."))
      .toBeInTheDocument();
  });
});
