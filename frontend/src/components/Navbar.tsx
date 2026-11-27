import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useTheme } from "../theme/ThemeProvider";
import { ExternalModulesMenu } from "./ExternalModulesMenu";

const linkBase =
  "shrink-0 whitespace-nowrap px-2.5 py-2 rounded-md text-sm font-medium transition-colors";

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
      <nav className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:px-6 lg:flex-row lg:flex-nowrap lg:items-center lg:justify-between lg:gap-4">
        <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:gap-4 lg:shrink-0">
          {/* Vermelho Mackenzie SOMENTE no logo */}
          <span className="shrink-0 whitespace-nowrap text-lg font-semibold text-white">
            Módulo<span className="text-brand-accent">6</span>
          </span>
          <div className="flex flex-wrap gap-1 lg:flex-nowrap">
            <TabLink to="/dashboard" label="Dashboard" />
            <TabLink to="/artefatos" label="Artefatos" />
            <TabLink to="/notificacoes" label="Notificações" badge={unreadBadge} />
            <TabLink to="/chat" label="Chat" badge={chatUnreadBadge} />
          </div>
        </div>

        <div className="flex min-w-0 flex-wrap items-center gap-2 lg:flex-nowrap lg:justify-end">
          <button
            type="button"
            onClick={toggle}
            className="shrink-0 whitespace-nowrap rounded-md px-2.5 py-2 text-sm font-medium text-white/90 hover:bg-primary-hover"
            aria-label="Alternar tema claro/escuro"
          >
            {theme === "light" ? "🌙 Escuro" : "☀️ Claro"}
          </button>
          {user && (
            <>
              <span
                className="min-w-0 max-w-full break-all text-sm text-white/80 lg:max-w-36 lg:truncate lg:break-normal xl:max-w-48"
                title={user.role ? `${user.user_id} · ${user.role}` : user.user_id}
              >
                {user.user_id}{user.role ? ` · ${user.role}` : ""}
              </span>
              <ExternalModulesMenu />
              <button
                type="button"
                onClick={logout}
                className="shrink-0 whitespace-nowrap rounded-md bg-primary-hover px-3 py-2 text-sm font-medium text-white hover:opacity-90"
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
  badge,
}: {
  to: string;
  label: string;
  badge?: number;
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `${linkBase} ${
          isActive ? "bg-primary-hover text-white" : "text-white/80 hover:bg-primary-hover"
        }`
      }
    >
      <span className="inline-flex items-center gap-2">
        {label}
        {badge && badge > 0 ? (
          <span className="metric inline-flex min-w-5 items-center justify-center rounded-full bg-priority-critical px-1.5 text-xs font-semibold text-white">
            {badge}
          </span>
        ) : null}
      </span>
    </NavLink>
  );
}
