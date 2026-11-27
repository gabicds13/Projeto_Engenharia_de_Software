import { NavLink } from "react-router-dom";
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

        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1 lg:flex-nowrap lg:overflow-x-auto" aria-label="Módulos e páginas">
          <ModuleLink number={1} label="Projetos" icon="▣" />
          <ModuleLink number={2} label="GitHub Sync" icon="☍" />
          <ModuleLink number={3} label="Artefatos" icon="▤" />
          <ModuleLink number={4} label="Code Review" icon="⚙" />
          <ModuleLink number={5} label="Curadoria" icon="★" />
          <TabLink to="/notificacoes" label="Notificações" icon="✉" badge={unreadBadge} />
          <ModuleLink number={7} label="MackAI" icon="✦" />
          <span className="hidden h-4 w-px shrink-0 bg-white/20 lg:block" aria-hidden="true" />
          <TabLink to="/dashboard" label="Dashboard" icon="▥" />
          <TabLink to="/artefatos" label="Artefatos do projeto" icon="▤" />
          <TabLink to="/chat" label="Chat" icon="◫" badge={chatUnreadBadge} />
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

function TabLink({
  to,
  label,
  icon,
  badge,
}: {
  to: string;
  label: string;
  icon: string;
  badge?: number;
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `${linkBase} ${isActive ? "bg-primary-hover text-white" : inactiveLink}`
      }
    >
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden="true">{icon}</span>
        {label}
        {badge && badge > 0 ? (
          <span className="metric inline-flex min-w-5 items-center justify-center rounded-full bg-priority-critical px-1 text-xs font-semibold text-white">
            {badge}
          </span>
        ) : null}
      </span>
    </NavLink>
  );
}
