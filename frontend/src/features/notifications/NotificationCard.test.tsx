import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Notification } from "../../lib/types";
import { NotificationCard } from "./NotificationCard";

function make(overrides: Partial<Notification> = {}): Notification {
  return {
    id: "ntf-1",
    source: "code_review",
    type: "review.critical_issue.found",
    priority: "critical",
    relevance_score: 0.95,
    reason: "Autor do PR e problema de segurança",
    classified_by: "llm",
    project_id: "proj-123",
    title: "Vulnerabilidade crítica no PR #42",
    body: "Credencial exposta.",
    link: null,
    created_at: new Date().toISOString(),
    read_at: null,
    ...overrides,
  };
}

describe("NotificationCard", () => {
  it("usa a cor da prioridade na borda esquerda (crítica)", () => {
    render(<NotificationCard notification={make({ priority: "critical" })} />);
    const card = screen.getByTestId("notification-card");
    expect(card.className).toContain("border-l-priority-critical");
    expect(card).toHaveAttribute("data-priority", "critical");
  });

  it("usa a cor correta para prioridade baixa", () => {
    render(<NotificationCard notification={make({ priority: "low" })} />);
    expect(screen.getByTestId("notification-card").className).toContain(
      "border-l-priority-low",
    );
  });

  it("mostra a origem com ícone + rótulo e o selo de prioridade", () => {
    render(<NotificationCard notification={make({ source: "github", priority: "high" })} />);
    expect(screen.getByText("GitHub")).toBeInTheDocument();
    expect(screen.getByText("ALTA")).toBeInTheDocument();
  });

  it("exibe horário relativo e título", () => {
    render(<NotificationCard notification={make()} />);
    expect(screen.getByText("Vulnerabilidade crítica no PR #42")).toBeInTheDocument();
    expect(screen.getByText(/agora|há/)).toBeInTheDocument();
  });
});
