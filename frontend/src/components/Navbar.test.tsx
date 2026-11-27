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

    expect(screen.getByRole("link", { name: /Dashboard/ })).toHaveAttribute("href", "/dashboard");
    expect(screen.getByRole("link", { name: /Artefatos/ })).toHaveAttribute("href", "/artefatos");
    expect(screen.getByRole("link", { name: /Notificações/ })).toHaveAttribute("href", "/notificacoes");
    expect(screen.getByRole("link", { name: /Chat/ })).toHaveAttribute("href", "/chat");
    expect(screen.getByRole("link", { name: /Notificações/ })).toHaveTextContent("3");
    expect(screen.getByRole("link", { name: /Chat/ })).toHaveTextContent("2");
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
    expect(links).toHaveClass("flex-wrap", "lg:flex-nowrap");
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
    expect(screen.getByText("Outros módulos").closest("details")).toHaveClass("shrink-0");
  });
});
