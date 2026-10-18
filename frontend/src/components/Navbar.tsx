import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useTheme } from "../theme/ThemeProvider";

const linkBase =
  "px-3 py-2 rounded-md text-md font-medium transition-colors";

export function Navbar({ unreadBadge }: { unreadBadge?: number }) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();

  return (
    <header className="bg-primary">
      <nav className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
        <div className="flex items-center gap-6">
          {/* Vermelho Mackenzie SOMENTE no logo */}
          <span className="text-lg font-semibold text-white">
            Módulo<span className="text-brand-accent">6</span>
          </span>
          <div className="flex gap-1">
            <TabLink to="/dashboard" label="Dashboard" />
            <TabLink to="/notificacoes" label="Notificações" badge={unreadBadge} />
            <TabLink to="/chat" label="Chat" />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={toggle}
            className="rounded-md px-3 py-2 text-sm font-medium text-white/90 hover:bg-primary-hover"
            aria-label="Alternar tema claro/escuro"
          >
            {theme === "light" ? "🌙 Escuro" : "☀️ Claro"}
          </button>
          {user && (
            <>
              <span className="text-sm text-white/80">
                {user.user_id} · {user.role}
              </span>
              <button
                type="button"
                onClick={logout}
                className="rounded-md bg-primary-hover px-3 py-2 text-sm font-medium text-white hover:opacity-90"
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
