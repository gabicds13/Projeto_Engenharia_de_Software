import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Navbar } from "./Navbar";

const mocks = vi.hoisted(() => ({
  logout: vi.fn(),
  toggle: vi.fn(),
  user: { user_id: "usuaria-teste", role: "DEV" as string | undefined },
}));

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    user: mocks.user,
    logout: mocks.logout,
  }),
}));

vi.mock("../theme/ThemeProvider", () => ({
  useTheme: () => ({ theme: "light", toggle: mocks.toggle }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mocks.user.user_id = "usuaria-teste";
  mocks.user.role = "DEV";
});

describe("Etapa 4 — navegação do portal", () => {
  it("oferece Dashboard, Notificações e Chat com os contadores", () => {
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Navbar unreadBadge={3} chatUnreadBadge={2} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/dashboard");
    expect(screen.getByRole("link", { name: "Artefatos do projeto" })).toHaveAttribute("href", "/artefatos");
    expect(screen.getByRole("link", { name: /Notificações/ })).toHaveAttribute("href", "/notificacoes");
    expect(screen.getByRole("link", { name: /Chat/ })).toHaveAttribute("href", "/chat");
    expect(screen.getByRole("link", { name: /Notificações/ })).toHaveTextContent("3");
    expect(screen.getByRole("link", { name: /Chat/ })).toHaveTextContent("2");
  });

  it("apresenta os atalhos comuns aos módulos na ordem do cabeçalho", () => {
    render(<MemoryRouter initialEntries={["/notificacoes"]}><Navbar /></MemoryRouter>);
    expect(screen.getByText("Engenharia de Software")).toBeInTheDocument();
    const links = screen.getAllByRole("link").slice(1);
    expect(links.map(link => link.getAttribute("href"))).toEqual([
      "https://green-river-02e44e810.2.azurestaticapps.net/",
      "https://ai-platform-github-service-eduardo-frapb8fbbcd0bfdm.brazilsouth-01.azurewebsites.net/",
      "https://modulo3-fhgjdpa6d5bbfvff.canadacentral-01.azurewebsites.net/app/",
      "https://revisor-codigo-ia-gio-ach9dbg3g9ekazf3.chilecentral-01.azurewebsites.net/",
      "https://frontmodulo5-ecaqg8fghzhyeuh2.brazilsouth-01.azurewebsites.net/",
      "/notificacoes",
      "https://mackai-conversas.calmfield-d7c6c49f.brazilsouth.azurecontainerapps.io/",
      "/dashboard",
      "/artefatos",
      "/chat",
    ]);
    for (const link of links.filter(link => link.getAttribute("href")?.startsWith("https:"))) {
      expect(link).not.toHaveAttribute("target");
    }
    expect(screen.getByRole("link", { name: "Notificações" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Artefatos" })).not.toHaveAttribute("aria-current");
  });

  it("separa o atalho externo do Módulo 3 da página interna de artefatos", () => {
    render(<MemoryRouter initialEntries={["/artefatos"]}><Navbar /></MemoryRouter>);
    const module3 = screen.getByRole("link", { name: "Artefatos" });
    const integrated = screen.getByRole("link", { name: "Artefatos do projeto" });
    expect(module3).toHaveAttribute("href", "https://modulo3-fhgjdpa6d5bbfvff.canadacentral-01.azurewebsites.net/app/");
    expect(module3).not.toHaveAttribute("target");
    expect(module3).not.toHaveAttribute("aria-current");
    expect(integrated).toHaveAttribute("href", "/artefatos");
    expect(integrated).toHaveAttribute("aria-current", "page");
  });

  it("mantém ações de tema e logout disponíveis", () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Alternar tema claro/escuro" }));
    fireEvent.click(screen.getByRole("button", { name: "Sair" }));
    expect(mocks.toggle).toHaveBeenCalledTimes(1);
    expect(mocks.logout).toHaveBeenCalledTimes(1);
  });

  it("usa layout com quebra e empilhamento para telas pequenas", () => {
    const { container } = render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    const nav = container.querySelector("nav");
    expect(nav).toHaveClass("flex-col");
    expect(nav).toHaveClass("lg:flex-row");
    const links = screen.getByRole("link", { name: /Dashboard/ }).parentElement;
    expect(links).toHaveClass("flex-wrap", "lg:flex-nowrap", "lg:overflow-x-auto");
    expect(nav).toHaveClass("lg:flex-nowrap");
  });

  it("mantém identificador longo em espaço limitado e não mostra separador sem papel", () => {
    const uuid = "12345678-1234-4abc-9876-123456789abc";
    mocks.user.user_id = uuid;
    mocks.user.role = undefined;
    render(
      <MemoryRouter>
        <Navbar unreadBadge={15} />
      </MemoryRouter>,
    );
    const identity = screen.getByTitle(uuid);
    expect(identity).toHaveTextContent(uuid);
    expect(identity).not.toHaveTextContent("·");
    expect(identity).toHaveClass("min-w-0", "lg:truncate");
    expect(screen.getByRole("button", { name: "Sair" })).toHaveClass("shrink-0");
    expect(screen.getByRole("link", { name: /Chat/ })).toHaveClass("shrink-0", "whitespace-nowrap");
    expect(screen.getByRole("link", { name: "Code Review" })).toHaveClass("shrink-0");
  });
});
