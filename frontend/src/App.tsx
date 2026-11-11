
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
    const loadChatUnread = async () => {
      try {
        const response = await api.get<Project[] | ProjectResponse>(
          "/api/bff/projects",
        );

        const projects = normalizeProjects(response);

        const counts = await Promise.all(
          projects.map(async (project) => {
            const projectId = getProjectId(project);

            if (!projectId) {
              return 0;
            }

            const result = await api.get<{
              project_id: string;
              unread: number;
            }>(
              `/api/bff/chat/rooms/${encodeURIComponent(projectId)}/unread`,
            );

            return result.unread;
          }),
        );

        setChatUnreadTotal(
          counts.reduce((total, count) => total + count, 0),
        );
      } catch {
        setChatUnreadTotal(0);
      }
    };

    void loadChatUnread();

    const timer = setInterval(() => {
      void loadChatUnread();
    }, 3000);

    return () => clearInterval(timer);
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
