
import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { LoginScreen } from "./auth/LoginScreen";
import { Navbar } from "./components/Navbar";
import { ChatPage } from "./features/chat/ChatPage";
import { DashboardPage } from "./features/dashboard/DashboardPage";
import { NotificationsPage } from "./features/notifications/NotificationsPage";
import {
  NotificationsProvider,
  useNotifications,
} from "./features/notifications/NotificationsContext";
import { Toasts } from "./features/notifications/Toasts";
import { ThemeProvider } from "./theme/ThemeProvider";
import { api } from "./lib/apiClient";

interface Project {
  id?: string;
  project_id?: string;
}

interface ProjectResponse {
  items?: Project[];
  projects?: Project[];
}

function normalizeProjects(
  response: Project[] | ProjectResponse,
): Project[] {
  if (Array.isArray(response)) {
    return response;
  }

  if (Array.isArray(response.items)) {
    return response.items;
  }

  if (Array.isArray(response.projects)) {
    return response.projects;
  }

  return [];
}

function getProjectId(project: Project): string {
  return project.project_id ?? project.id ?? "";
}
function ShellContent() {
  const { unreadTotal } = useNotifications();
  const [chatUnreadTotal, setChatUnreadTotal] = useState(0);
  useEffect(() => {
    let mounted = true;
    let projectIds: string[] = [];
    let inFlight = false;

    const loadChatUnread = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        // Projetos mudam raramente: nao buscar de novo a cada verificacao.
        if (projectIds.length === 0) {
          const response = await api.get<Project[] | ProjectResponse>(
            "/api/bff/projects",
          );
          projectIds = normalizeProjects(response)
            .map(getProjectId)
            .filter(Boolean);
        }

        const counts = await Promise.all(
          projectIds.map(async (projectId) => {
            const result = await api.get<{ project_id: string; unread: number }>(
              `/api/bff/chat/rooms/${encodeURIComponent(projectId)}/unread`,
            );
            return result.unread;
          }),
        );
        if (mounted) {
          setChatUnreadTotal(counts.reduce((sum, count) => sum + count, 0));
        }
      } catch {
        // Falhas temporarias nao apagam o numero anterior da interface.
      } finally {
        inFlight = false;
      }
    };

    void loadChatUnread();
    const timer = setInterval(() => void loadChatUnread(), 15_000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  return (
    <div className="min-h-full bg-bg text-text">

      <Navbar
       unreadBadge={unreadTotal}
       chatUnreadBadge={chatUnreadTotal}
      />
      <main className="mx-auto max-w-6xl p-6">
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/notificacoes" element={<NotificationsPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
      <Toasts />
    </div>
  );
}

function Shell() {
  const { user } = useAuth();
  if (!user) return <LoginScreen />;
  return (
    <NotificationsProvider>
      <ShellContent />
    </NotificationsProvider>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Shell />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
