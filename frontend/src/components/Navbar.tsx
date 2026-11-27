import { useEffect, useId, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useTheme } from "../theme/ThemeProvider";
import { EXTERNAL_MODULES } from "./ExternalModulesMenu";

const linkBase =
  "shrink-0 whitespace-nowrap rounded-md px-2 py-1.5 text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-white";

const inactiveLink = "text-white/90 hover:bg-primary-hover hover:text-white";

function ModuleLink({ number, label, icon }: { number: number; label: string; icon: string }) {
  const module = EXTERNAL_MODULES.find(item => item.number === number);
  if (!module) return null;
  return (
    <a href={module.url}
      className={`${linkBase} ${inactiveLink}`}
      title={`Abrir ${label}`}>
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden="true">{icon}</span>{label}
      </span>
    </a>
  );
}

export function Navbar({
  unreadBadge,
  chatUnreadBadge,
}: {
  unreadBadge?: number;
  chatUnreadBadge?: number;
}) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();

  return (
    <header className="bg-primary">
      <nav aria-label="Navegação principal" className="flex w-full flex-col gap-2 px-3 py-2 lg:flex-row lg:flex-nowrap lg:items-center lg:gap-3">
        <NavLink to="/dashboard" className="shrink-0 whitespace-nowrap text-xs font-semibold text-white lg:border-r lg:border-white/20 lg:pr-3"
          title="Engenharia de Software — Módulo 6">
          Engenharia de Software<span className="text-brand-accent">.</span>
        </NavLink>

        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1 xl:flex-nowrap" aria-label="Módulos da plataforma">
          <ModuleLink number={1} label="Projetos" icon="▣" />
          <ModuleLink number={2} label="GitHub Sync" icon="☍" />
          <ModuleLink number={3} label="Artefatos" icon="▤" />
          <ModuleLink number={4} label="Code Review" icon="⚙" />
          <ModuleLink number={5} label="Curadoria" icon="★" />
          <Module6Menu unreadBadge={unreadBadge} chatUnreadBadge={chatUnreadBadge} />
          <ModuleLink number={7} label="MackAI" icon="✦" />
        </div>

        <div className="flex min-w-0 flex-wrap items-center gap-2 lg:shrink-0 lg:flex-nowrap lg:justify-end">
          <button
            type="button"
            onClick={toggle}
            className="shrink-0 whitespace-nowrap rounded-md px-2 py-1.5 text-xs font-medium text-white hover:bg-primary-hover"
            aria-label="Alternar tema claro/escuro"
            title={theme === "light" ? "Ativar modo escuro" : "Ativar modo claro"}
          >
            <span aria-hidden="true">{theme === "light" ? "☾" : "☀"}</span>
            <span className="ml-1 lg:hidden 2xl:inline">{theme === "light" ? "Escuro" : "Claro"}</span>
          </button>
          {user && (
            <>
              <span
                className="min-w-0 max-w-full break-all text-xs text-white/80 lg:max-w-16 lg:truncate lg:break-normal 2xl:max-w-36"
                title={user.role ? `${user.user_id} · ${user.role}` : user.user_id}
              >
                {user.user_id}{user.role ? ` · ${user.role}` : ""}
              </span>
              <button
                type="button"
                onClick={logout}
                className="shrink-0 whitespace-nowrap rounded-md bg-primary-hover px-2 py-1.5 text-xs font-medium text-white hover:opacity-90"
              >
                Sair
              </button>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}

function Module6Menu({ unreadBadge, chatUnreadBadge }: { unreadBadge?: number; chatUnreadBadge?: number }) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const { pathname } = useLocation();

  useEffect(() => { setOpen(false); }, [pathname]);

  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (event.target instanceof Node && !menuRef.current?.contains(event.target)) {
        setOpen(false);
      }
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  const close = () => setOpen(false);

  return (
    <div ref={menuRef} className="relative shrink-0">
      <button ref={triggerRef} type="button" aria-expanded={open} aria-controls={menuId}
        onClick={() => setOpen(value => !value)}
        className={`${linkBase} inline-flex items-center gap-1.5 bg-primary-hover text-white`}>
        <span aria-hidden="true">✉</span>
        Notificações
        <CountBadge value={unreadBadge} />
        <span aria-hidden="true" className={open ? "rotate-180" : ""}>▾</span>
      </button>
      <div id={menuId} hidden={!open}
        className="z-50 mt-1 w-56 max-w-[calc(100vw-2rem)] rounded-lg border border-border bg-surface p-1.5 text-text shadow-lg lg:absolute lg:left-0 lg:top-full">
        {open && (
          <div aria-label="Páginas do Módulo 6" className="flex flex-col gap-1">
            <p className="px-3 py-1 text-xs font-semibold text-text-muted">Módulo 6</p>
            <TabLink to="/dashboard" label="Dashboard" icon="▥" onClick={close} />
            <TabLink to="/artefatos" label="Artefatos do projeto" icon="▤" onClick={close} />
            <TabLink to="/notificacoes" label="Notificações" icon="✉" badge={unreadBadge} onClick={close} />
            <TabLink to="/chat" label="Chat" icon="◫" badge={chatUnreadBadge} onClick={close} />
          </div>
        )}
      </div>
    </div>
  );
}

function CountBadge({ value }: { value?: number }) {
  return value && value > 0 ? (
    <span className="metric inline-flex min-w-5 items-center justify-center rounded-full bg-priority-critical px-1 text-xs font-semibold text-white">
      {value}
    </span>
  ) : null;
}

function TabLink({
  to,
  label,
  icon,
  badge,
  onClick,
}: {
  to: string;
  label: string;
  icon: string;
  badge?: number;
  onClick: () => void;
}) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className={({ isActive }) =>
        `${linkBase} block px-3 py-2 ${isActive ? "bg-primary text-white" : "text-text hover:bg-bg"}`
      }
    >
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden="true">{icon}</span>
        {label}
        <CountBadge value={badge} />
      </span>
    </NavLink>
  );
}
