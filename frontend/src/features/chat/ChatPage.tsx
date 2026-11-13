import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { DirectChatPanel } from "./DirectChatPanel";
import { UnavailableState } from "../../components/UnavailableState";
import { useWebSocket } from "../../hooks/useWebSocket";
import { api, ApiError, getToken } from "../../lib/apiClient";
import { wsUrl } from "../../lib/config";
import type { ChatHistoryResult, ChatMessage } from "../../lib/types";

interface Project {
  id?: string;
  project_id?: string;
  name?: string;
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

export function ChatPage() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [chatMode, setChatMode] = useState<"general" | "direct">("general");
  const [projectId, setProjectId] = useState("");
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [unread, setUnread] = useState(0);
  const [available, setAvailable] = useState(true);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const activeProjectRef = useRef(projectId);
  activeProjectRef.current = projectId;
  const seen = useRef<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);


  useEffect(() => {
    const loadProjects = async () => {
      setProjectsLoading(true);

      try {
        const response = await api.get<Project[] | ProjectResponse>(
          "/api/bff/projects",
        );

        const list = normalizeProjects(response);

        setProjects(list);

        if (list.length > 0) {
          setProjectId(getProjectId(list[0]));
        }
      } catch {
        setProjects([]);
      } finally {
        setProjectsLoading(false);
      }
    };

    void loadProjects();
  }, []);
  const loadUnread = useCallback(async () => {
    if (!projectId) {
      setUnread(0);
      return;
    }

    try {
      const response = await api.get<{
        project_id: string;
        unread: number;
      }>(
        `/api/bff/chat/rooms/${encodeURIComponent(projectId)}/unread`,
      );

      setUnread(response.unread);
    } catch {
      setUnread(0);
    }
  }, [projectId]);

  const markRead = useCallback(async () => {
    if (!projectId) {
      return;
    }

    try {
      await api.post<void>(
        `/api/bff/chat/rooms/${encodeURIComponent(projectId)}/read`,
      );

      setUnread(0);
    } catch {
      // Se falhar, o chat continua funcionando normalmente.
    }
  }, [projectId]);

  const loadHistory = useCallback(async () => {
    if (!projectId) return;
    const requestedProjectId = projectId;
    try {
      const res = await api.get<ChatHistoryResult>(
        `/api/bff/chat/rooms/${encodeURIComponent(requestedProjectId)}/messages`,
      );
      // Não mostrar mensagens da resposta atrasada de outro projeto.
      if (activeProjectRef.current !== requestedProjectId) return;
      if (res.state === "unavailable") {
        setAvailable(false);
        return;
      }
      setAvailable(true);
      res.messages.forEach((m) => seen.current.add(m.id));
      setMessages(res.messages);
    } catch {
      if (activeProjectRef.current === requestedProjectId) setAvailable(false);
    }
  }, [projectId]);

  const onMessage = useCallback((data: unknown) => {
    const msg = data as { event?: string; data?: ChatMessage };
    if (msg.event === "chat.message" && msg.data) {
      const m = msg.data;
      if (m.project_id !== activeProjectRef.current || seen.current.has(m.id)) return;
      seen.current.add(m.id);
      setMessages((prev) => [...prev, m]);
      void markRead();
    }
  }, [markRead]);

  const token = getToken();

  const socketUrl =
    projectId && token
      ? wsUrl(`/ws/chat?project_id=${encodeURIComponent(projectId)}`)
      : null;

  const status = useWebSocket(socketUrl, {
    onMessage,
    onReconnect: loadHistory,
    enabled: !!projectId,
    authToken: token ?? undefined,
  });

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    if (!projectId) {
      return;
    }

    void loadUnread();
    void markRead();
  }, [projectId, loadUnread, markRead]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const content = text.trim();
    const requestedProjectId = projectId;
    if (!content || !requestedProjectId || sending) return;
    setSending(true);
    setSendError(null);
    try {
      const created = await api.post<ChatMessage>(
        `/api/bff/chat/rooms/${encodeURIComponent(requestedProjectId)}/messages`,
        { content },
      );
      if (activeProjectRef.current !== requestedProjectId) return;
      // Só limpa após confirmação e não apaga texto novo digitado durante o envio.
      setText((current) => current.trim() === content ? "" : current);
      if (!seen.current.has(created.id)) {
        seen.current.add(created.id);
        setMessages((prev) => [...prev, created]);
      }
    } catch (err) {
      if (activeProjectRef.current === requestedProjectId) {
        setSendError(err instanceof ApiError ? err.message : "Não foi possível enviar a mensagem. Tente novamente.");
      }
    } finally {
      setSending(false);
    }
  };


  if (projectsLoading) {
    return <p className="text-text-muted">Carregando projetos…</p>;
  }

  if (!projectId) {
    return (
      <p className="rounded-lg border border-border bg-surface p-6 text-text-muted">
        Nenhum projeto disponível para este usuário.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          <button type="button" onClick={() => setChatMode("general")}
            className={`rounded-md px-3 py-2 text-sm font-medium ${chatMode === "general" ? "bg-primary text-white" : "border border-border bg-surface text-text"}`}>
            Chat geral
          </button>
          <button type="button" onClick={() => setChatMode("direct")}
            className={`rounded-md px-3 py-2 text-sm font-medium ${chatMode === "direct" ? "bg-primary text-white" : "border border-border bg-surface text-text"}`}>
            Conversas privadas
          </button>
        </div>
      </div>
      {chatMode === "direct" ? (
        <DirectChatPanel projectId={projectId} currentUserId={user?.user_id ?? ""} />
      ) : !available ? (
        <div className="flex flex-col items-start gap-3">
          <UnavailableState label="Chat geral" />
          <button type="button" onClick={() => void loadHistory()}
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white">
            Tentar novamente
          </button>
        </div>
      ) : (
    <section className="flex h-[70vh] flex-col rounded-lg border border-border bg-surface">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-lg font-semibold text-text">Chat</h1>
            <div className="flex items-center gap-2">
            <p className="text-xs text-text-muted"># Geral</p>

  {unread > 0 && (
    <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-semibold text-white">
      {unread}
    </span>
  )}
</div>
          </div>

          <select
            value={projectId}
            onChange={(event) => {
              activeProjectRef.current = event.target.value;
              seen.current.clear();
              setMessages([]);
              setAvailable(true);
              setSendError(null);
              setText("");
              setProjectId(event.target.value);
            }}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text"
          >
            {projects.map((project) => {
              const id = getProjectId(project);

              return (
                <option key={id} value={id}>
                  {project.name ?? id}
                </option>
              );
            })}
          </select>
        </div>
        <span
          className={`h-2 w-2 rounded-full ${status === "open" ? "bg-success" : "bg-priority-low"}`}
          title={status === "open" ? "Conectado" : "Reconectando…"}
        />
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <p className="text-center text-sm text-text-muted">Nenhuma mensagem ainda.</p>
        ) : (
          messages.map((m) => <MessageBubble key={m.id} message={m} mine={m.author_id === user?.user_id} />)
        )}
        <div ref={bottomRef} />
      </div>

      {sendError && <p role="alert" className="px-3 text-sm text-priority-critical">{sendError}</p>}
      <form onSubmit={send} className="flex gap-2 border-t border-border p-3">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Escreva uma mensagem…"
          className="min-w-0 flex-1 rounded-md border border-border bg-bg px-3 py-2 text-sm text-text"
        />
        <button
          type="submit"
          disabled={sending || !text.trim()}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {sending ? "Enviando…" : "Enviar"}
        </button>
      </form>
    </section>
      )}
    </div>
  );
}

function MessageBubble({ message, mine }: { message: ChatMessage; mine: boolean }) {
  const time = new Date(message.created_at).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <div className={`flex flex-col ${mine ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${mine ? "bg-primary text-white" : "border border-border bg-bg text-text"
          }`}
      >
        {!mine && <p className="text-xs font-semibold text-text-muted">{message.author_id}</p>}
        <p>{message.content}</p>
      </div>
      <span className="metric mt-0.5 text-xs text-text-muted">{time}</span>
    </div>
  );
}
