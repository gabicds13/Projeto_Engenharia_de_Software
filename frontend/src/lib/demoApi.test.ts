import { describe, expect, it } from "vitest";
import { demoRequest } from "./demoApi";
import type { DashboardResponse, ListResult, Notification } from "./types";

describe("API local para capturas de tela", () => {
  it("mostra projetos e um dashboard identificado como simulado", async () => {
    const projects = await demoRequest<Array<{ project_id: string }>>("/api/bff/projects");
    expect(projects[0].project_id).toBe("projeto-demo-modulo6");
    const data = await demoRequest<DashboardResponse>("/api/bff/dashboard?project_id=projeto-demo-modulo6");
    expect(data.project_id).toBe("projeto-demo-modulo6");
    expect(data.weekly.data_origin).toBe("mock");
  });

  it("marca notificacoes ficticias como lidas", async () => {
    const page = await demoRequest<ListResult>("/api/bff/notifications");
    const target = page.page!.items.find((n: Notification) => !n.read_at);
    expect(target).toBeDefined();
    await demoRequest("/api/bff/notifications/" + target!.id, "PATCH");
    const after = await demoRequest<ListResult>("/api/bff/notifications");
    expect(after.page!.items.find(n => n.id === target!.id)?.read_at).toBeTruthy();
  });

  it("envia mensagem ficticia sem requisicao HTTP", async () => {
    const project = "projeto-demo-modulo6";
    const msg = await demoRequest<{ content: string }>(`/api/bff/chat/rooms/${project}/messages`, "POST", { content: "Teste de tela" });
    expect(msg.content).toBe("Teste de tela");
  });

  it("nunca aceita login real na API simulada", async () => {
    await expect(demoRequest("/api/bff/auth/login", "POST", { email: "x", password: "x" }))
      .rejects.toThrow("Rota não implementada");
  });
});
