import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MetricCard, MetricNumber } from "./MetricCard";

describe("identificação de dados simulados", () => {
  it("sinaliza métricas mockadas no dashboard", () => {
    render(
      <MetricCard label="Commits na semana" state="ok" dataOrigin="mock">
        <MetricNumber value={47} />
      </MetricCard>,
    );
    expect(screen.getByText("47")).toBeInTheDocument();
    expect(screen.getByText("Dados de demonstração (simulados)")).toBeInTheDocument();
  });

  it("não identifica dados reais como simulados", () => {
    render(
      <MetricCard label="User Stories" state="ok" dataOrigin="real">
        <MetricNumber value={1} />
      </MetricCard>,
    );
    expect(screen.queryByText("Dados de demonstração (simulados)")).not.toBeInTheDocument();
  });

  it("não mostra dados numéricos quando o serviço estiver indisponível", () => {
    render(
      <MetricCard label="GitHub" state="unavailable" dataOrigin="mock">
        <MetricNumber value={47} />
      </MetricCard>,
    );
    expect(screen.getByText("indisponível no momento")).toBeInTheDocument();
    expect(screen.queryByText("47")).not.toBeInTheDocument();
  });
});
