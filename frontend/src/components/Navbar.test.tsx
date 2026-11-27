import { fireEvent, render, screen, within } from "@testing-library/react";
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

describe("Navegação do portal", () => {
  it("mantém as quatro páginas e contadores visíveis sem abrir menus", () => {
    render(<MemoryRouter initialEntries={["/dashboard"]}><Navbar unreadBadge={3} chatUnreadBadge={2} /></MemoryRouter>);
    const local = within(screen.getByRole("navigation", { name: "Páginas do Módulo 6" }));
    expect(local.getByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/dashboard");
    expect(local.getByRole("link", { name: "Dashboard" })).toHaveAttribute("aria-current", "page");
    expect(local.getByRole("link", { name: "Artefatos do projeto" })).toHaveAttribute("href", "/artefatos");
    expect(local.getByRole("link", { name: /Notificações/ })).toHaveAttribute("href", "/notificacoes");
    expect(local.getByRole("link", { name: /Chat/ })).toHaveAttribute("href", "/chat");
    expect(local.getByRole("link", { name: /Notificações/ })).toHaveTextContent("3");
    expect(local.getByRole("link", { name: /Chat/ })).toHaveTextContent("2");
  });

  it("apresenta os atalhos comuns na ordem do cabeçalho, abrindo na mesma aba", () => {
    render(<MemoryRouter initialEntries={["/notificacoes"]}><Navbar /></MemoryRouter>);
    const main = within(screen.getByRole("navigation", { name: "Navegação principal" }));
    expect(main.getByText("Engenharia de Software")).toBeInTheDocument();
    const links = main.getAllByRole("link").slice(1);
    expect(links.map(link => link.getAttribute("href"))).toEqual([
      "https://green-river-02e44e810.2.azurestaticapps.net/",
      "https://ai-platform-github-service-eduardo-frapb8fbbcd0bfdm.brazilsouth-01.azurewebsites.net/",
      "https://modulo3-fhgjdpa6d5bbfvff.canadacentral-01.azurewebsites.net/app/",
      "https://revisor-codigo-ia-gio-ach9dbg3g9ekazf3.chilecentral-01.azurewebsites.net/",
      "https://frontmodulo5-ecaqg8fghzhyeuh2.brazilsouth-01.azurewebsites.net/",
      "/notificacoes",
      "https://mackai-conversas.calmfield-d7c6c49f.brazilsouth.azurecontainerapps.io/",
    ]);
    for (const link of links) expect(link).not.toHaveAttribute("target");
    expect(main.getByRole("link", { name: "Notificações" })).toHaveAttribute("aria-current", "location");
    expect(main.getByRole("link", { name: "Artefatos" })).not.toHaveAttribute("aria-current");
  });

  it("separa os artefatos externos da página integrada e mantém as abas ao navegar", () => {
    render(<MemoryRouter initialEntries={["/artefatos"]}><Navbar /></MemoryRouter>);
    const module3 = screen.getByRole("link", { name: "Artefatos" });
    const local = within(screen.getByRole("navigation", { name: "Páginas do Módulo 6" }));
    const integrated = local.getByRole("link", { name: "Artefatos do projeto" });
    expect(module3).toHaveAttribute("href", "https://modulo3-fhgjdpa6d5bbfvff.canadacentral-01.azurewebsites.net/app/");
    expect(module3).not.toHaveAttribute("target");
    expect(integrated).toHaveAttribute("href", "/artefatos");
    expect(integrated).toHaveAttribute("aria-current", "page");
    fireEvent.click(local.getByRole("link", { name: "Chat" }));
    expect(local.getByRole("link", { name: "Chat" })).toHaveAttribute("aria-current", "page");
    expect(integrated).not.toHaveAttribute("aria-current");
    fireEvent.click(local.getByRole("link", { name: "Dashboard" }));
    expect(local.getByRole("link", { name: "Dashboard" })).toHaveAttribute("aria-current", "page");
    expect(local.getAllByRole("link")).toHaveLength(4);
  });

  it("mantém ações de tema e logout disponíveis", () => {
    render(<MemoryRouter><Navbar /></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Alternar tema claro/escuro" }));
    fireEvent.click(screen.getByRole("button", { name: "Sair" }));
    expect(mocks.toggle).toHaveBeenCalledTimes(1);
    expect(mocks.logout).toHaveBeenCalledTimes(1);
  });

  it("usa duas linhas independentes e responsivas", () => {
    render(<MemoryRouter><Navbar /></MemoryRouter>);
    const nav = screen.getByRole("navigation", { name: "Navegação principal" });
    const local = screen.getByRole("navigation", { name: "Páginas do Módulo 6" });
    expect(nav).toHaveClass("flex-col", "lg:flex-row", "lg:flex-nowrap");
    expect(within(nav).getByRole("link", { name: "Projetos" }).parentElement).toHaveClass("flex-wrap", "xl:flex-nowrap");
    expect(local).toHaveClass("flex-wrap");
    expect(nav).not.toContainElement(local);
  });

  it("mantém identificador longo em espaço limitado e não mostra separador sem papel", () => {
    const uuid = "12345678-1234-4abc-9876-123456789abc";
    mocks.user.user_id = uuid;
    mocks.user.role = undefined;
    render(<MemoryRouter><Navbar unreadBadge={15} /></MemoryRouter>);
    const identity = screen.getByTitle(uuid);
    expect(identity).toHaveTextContent(uuid);
    expect(identity).not.toHaveTextContent("·");
    expect(identity).toHaveClass("min-w-0", "lg:truncate");
    expect(screen.getByRole("button", { name: "Sair" })).toHaveClass("shrink-0");
    expect(screen.getByRole("link", { name: /Chat/ })).toHaveClass("shrink-0", "whitespace-nowrap");
    expect(screen.getByRole("link", { name: "Code Review" })).toHaveClass("shrink-0");
  });
});
