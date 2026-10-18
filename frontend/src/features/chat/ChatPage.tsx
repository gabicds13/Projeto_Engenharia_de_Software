import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { UnavailableState } from "../../components/UnavailableState";
import { useWebSocket } from "../../hooks/useWebSocket";
import { api, ApiError, getToken } from "../../lib/apiClient";
import { wsUrl } from "../../lib/config";
import type { ChatHistoryResult, ChatMessage } from "../../lib/types";

export function ChatPage() {
  const { user } = useAuth();
  const projectId = user?.project_ids[0] ?? "";
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [available, setAvailable] = useState(true);
  const [text, setText] = useState("");
  const seen = useRef<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadHistory = useCallback(async () => {
    if (!projectId) return;
    try {
      const res = await api.get<ChatHistoryResult>(
        `/api/bff/chat/rooms/${encodeURIComponent(projectId)}/messages`,
      );
      if (res.state === "unavailable") {
        setAvailable(false);
        return;
      }
      setAvailable(true);
      res.messages.forEach((m) => seen.current.add(m.id));
      setMessages(res.messages);
    } catch {
      setAvailable(false);
    }
  }, [projectId]);

  const onMessage = useCallback((data: unknown) => {
    const msg = data as { event?: string; data?: ChatMessage };
    if (msg.event === "chat.message" && msg.data) {
      const m = msg.data;
      if (seen.current.has(m.id)) return;
      seen.current.add(m.id);
      setMessages((prev) => [...prev, m]);
    }
  }, []);

  const socketUrl =
    projectId && getToken()
      ? wsUrl(`/ws/chat?project_id=${encodeURIComponent(projectId)}&token=${getToken()}`)
      : null;
  const status = useWebSocket(socketUrl, { onMessage, onReconnect: loadHistory, enabled: !!projectId });

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const content = text.trim();
    if (!content) return;
    setText("");
    try {
      const created = await api.post<ChatMessage>(
        `/api/bff/chat/rooms/${encodeURIComponent(projectId)}/messages`,
        { content },
      );
      if (!seen.current.has(created.id)) {
        seen.current.add(created.id);
        setMessages((prev) => [...prev, created]);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status >= 500) setAvailable(false);
    }
  };

  if (!available) return <UnavailableState label="Chat" />;

  return (
    <section className="flex h-[70vh] flex-col rounded-lg border border-border bg-surface">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <h1 className="text-lg font-semibold text-text">Chat · {projectId}</h1>
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

      <form onSubmit={send} className="flex gap-2 border-t border-border p-3">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Escreva uma mensagem…"
          className="flex-1 rounded-md border border-border bg-bg px-3 py-2 text-sm text-text"
        />
        <button
          type="submit"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
        >
          Enviar
        </button>
      </form>
    </section>
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
        className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
          mine ? "bg-primary text-white" : "border border-border bg-bg text-text"
        }`}
      >
        {!mine && <p className="text-xs font-semibold text-text-muted">{message.author_id}</p>}
        <p>{message.content}</p>
      </div>
      <span className="metric mt-0.5 text-xs text-text-muted">{time}</span>
    </div>
  );
}
