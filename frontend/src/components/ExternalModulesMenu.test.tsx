import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ExternalModulesMenu } from "./ExternalModulesMenu";

describe("Menu de outros módulos", () => {
  it("mostra interfaces públicas e abre em outra aba com proteção", () => {
    render(<ExternalModulesMenu />);
    fireEvent.click(screen.getByText("Outros módulos"));

    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(5);
    expect(screen.getByText("Módulo 1")).toBeInTheDocument();
    expect(screen.getByText("Módulo 2")).toBeInTheDocument();
    expect(screen.getByText("Módulo 4")).toBeInTheDocument();
    expect(screen.getByText("Módulo 5")).toBeInTheDocument();
    expect(screen.getByText("Módulo 7")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Módulo 4/ }))
      .toHaveAttribute("href", "https://revisor-codigo-ia-gio-ach9dbg3g9ekazf3.chilecentral-01.azurewebsites.net/");
    for (const link of links) {
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
      expect(link.getAttribute("href")).toMatch(/^https:\/\//);
    }
  });

  it("fecha ao pressionar Escape e devolve foco ao acionador", () => {
    const { container } = render(<ExternalModulesMenu />);
    const details = container.querySelector("details");
    const summary = screen.getByText("Outros módulos");
    fireEvent.click(summary);
    expect(details).toHaveAttribute("open");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(details).not.toHaveAttribute("open");
    expect(summary).toHaveFocus();
  });

  it("fecha após clicar em um destino", () => {
    const { container } = render(<ExternalModulesMenu />);
    fireEvent.click(screen.getByText("Outros módulos"));
    fireEvent.click(screen.getByRole("link", { name: /Módulo 5/ }));
    expect(container.querySelector("details")).not.toHaveAttribute("open");
  });
});
