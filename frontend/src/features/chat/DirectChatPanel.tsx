import { useCallback, useEffect, useRef, useState } from "react";
import { useWebSocket } from "../../hooks/useWebSocket";
import { api, ApiError, getToken } from "../../lib/apiClient";
import { wsUrl } from "../../lib/config";

interface DirectChannel {
  id: string;
  project_id: string;
  type: string;
  member_ids: string[];
  created_at: string;
}

interface DirectMessage {
  id: string;
  channel_id: string;
  project_id: string;
  author_id: string;
  content: string;
  created_at: string;
}

interface NewChannel {
  id: string;
}

interface DirectEvent {
  event?: string;
  data?: DirectMessage;
}

function otherMember(channel: DirectChannel, me: string): string {
  return channel.member_ids.find((id) => id !== me) ?? "Conversa privada";
}

export function DirectChatPanel({
  projectId,
  currentUserId,
}: {
  projectId: string;
  currentUserId: string;
}) {
  const [channels, setChannels] = useState<DirectChannel[]>([]);
  const [channelId, setChannelId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [messages, setMessages] = useState<DirectMessage[]>([]);
  const [unread, setUnread] = useState<Record<string, number>>({});
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const seen = useRef<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);

  const basePath = `/api/bff/chat/rooms/${encodeURIComponent(projectId)}/direct`;

  const loadChannels = useCallback(async () => {
    try {
      const list = await api.get<DirectChannel[]>(basePath);
      setChannels(list);
      const counts = await Promise.all(
        list.map(async (channel) => {
          try {
            const result = await api.get<{ unread: number }>(
              `${basePath}/${encodeURIComponent(channel.id)}/unread`,
            );
            return [channel.id, result.unread] as const;
          } catch {
            return [channel.id, 0] as const;
          }
        }),
      );
      setUnread(Object.fromEntries(counts));
      setError("");
    } catch {
      setError("Não foi possível carregar as conversas privadas. Verifique se o banco de dados do chat está ativo.");
    }
  }, [basePath]);

  const loadMessages = useCallback(async () => {
    if (!channelId) return;
    try {
      const list = await api.get<DirectMessage[]>(
        `${basePath}/${encodeURIComponent(channelId)}/messages`,
      );
      seen.current = new Set(list.map((item) => item.id));
      setMessages(list);
      setError("");
    } catch {
      setError("Não foi possível carregar o histórico desta conversa.");
    }
  }, [basePath, channelId]);

  const markRead = useCallback(async () => {
    if (!channelId) return;
    try {
      await api.post(`${basePath}/${encodeURIComponent(channelId)}/read`);
      setUnread((previous) => ({ ...previous, [channelId]: 0 }));
    } catch {
      // Uma falha ao marcar como lida não interrompe a conversa.
    }
  }, [basePath, channelId]);

  useEffect(() => {
    setChannels([]);
    setChannelId("");
    setTargetId("");
    setMessages([]);
    setUnread({});
    seen.current.clear();
    void loadChannels();
  }, [projectId, loadChannels]);

  useEffect(() => {
    seen.current.clear();
    setMessages([]);
    void loadMessages();
    void markRead();
  }, [channelId, loadMessages, markRead]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const onMessage = useCallback(
    (payload: unknown) => {
      const message = payload as DirectEvent;
      if (message.event !== "chat.direct.message" || !message.data) return;
      if (seen.current.has(message.data.id)) return;
      seen.current.add(message.data.id);
      setMessages((previous) => [...previous, message.data!]);
      void markRead();
    },
    [markRead],
  );

  const token = getToken();
  const url =
    channelId && token
      ? wsUrl(
          `/ws/chat/direct?project_id=${encodeURIComponent(projectId)}&channel_id=${encodeURIComponent(channelId)}`,
        )
      : null;

  const socketStatus = useWebSocket(url, {
    onMessage,
    onReconnect: loadMessages,
    enabled: !!channelId && !!token,
    authToken: token ?? undefined,
  });

  const startConversation = async (event: React.FormEvent) => {
    event.preventDefault();
    const target = targetId.trim();
    if (!target || target === currentUserId) {
      setError("Informe o ID de outro integrante.");
      return;
    }
    setCreating(true);
    try {
      const result = await api.post<NewChannel>(basePath, {
        target_user_id: target,
      });
      await loadChannels();
      setChannelId(result.id);
      setTargetId("");
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Não foi possível abrir a conversa.");
    } finally {
      setCreating(false);
    }
  };

  const send = async (event: React.FormEvent) => {
    event.preventDefault();
    const content = text.trim();
    if (!content || !channelId) return;
    try {
      const message = await api.post<DirectMessage>(
        `${basePath}/${encodeURIComponent(channelId)}/messages`,
        { content },
      );
      setText("");
      if (!seen.current.has(message.id)) {
        seen.current.add(message.id);
        setMessages((previous) => [...previous, message]);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Não foi possível enviar a mensagem.");
    }
  };

  return (
    <div className="grid min-h-[60vh] gap-4 md:grid-cols-[15rem_1fr]">
      <aside className="rounded-lg border border-border bg-surface p-3">
        <h2 className="mb-3 font-semibold text-text">Conversas privadas</h2>
        <form onSubmit={(event) => void startConversation(event)} className="mb-4 flex flex-col gap-2">
          <label htmlFor="direct-target" className="text-xs text-text-muted">
            ID do integrante do projeto
          </label>
          <input
            id="direct-target"
            value={targetId}
            onChange={(event) => setTargetId(event.target.value)}
            placeholder="ID do usuário"
            className="w-full rounded-md border border-border bg-bg px-2 py-2 text-sm text-text"
          />
          <button
            disabled={creating || !targetId.trim()}
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {creating ? "Abrindo..." : "Nova conversa"}
          </button>
        </form>
        {channels.length === 0 && (
          <p className="text-xs text-text-muted">Nenhuma conversa privada ainda.</p>
        )}
        <div className="space-y-2">
          {channels.map((channel) => (
            <button
              key={channel.id}
              type="button"
              onClick={() => setChannelId(channel.id)}
              className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm ${
                channelId === channel.id
                  ? "bg-primary text-white"
                  : "bg-bg text-text hover:bg-border"
              }`}
            >
              <span className="truncate">@{otherMember(channel, currentUserId)}</span>
              {(unread[channel.id] ?? 0) > 0 && (
                <span className="ml-2 rounded-full bg-priority-critical px-2 py-0.5 text-xs text-white">
                  {unread[channel.id]}
                </span>
              )}
            </button>
          ))}
        </div>
      </aside>

      <section className="flex min-h-[60vh] flex-col rounded-lg border border-border bg-surface">
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="font-semibold text-text">
            {channelId ? "Conversa privada" : "Selecione ou inicie uma conversa"}
          </h2>
          {channelId && (
            <span className="text-xs text-text-muted">
              {socketStatus === "open" ? "Conectado" : "Reconectando..."}
            </span>
          )}
        </header>
        {error && <p role="alert" className="m-3 rounded-md border border-border p-2 text-sm text-text">{error}</p>}
        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex flex-col ${
                message.author_id === currentUserId ? "items-end" : "items-start"
              }`}
            >
              <p className="max-w-[85%] break-words rounded-lg bg-bg px-3 py-2 text-sm text-text">
                {message.author_id !== currentUserId && (
                  <span className="block text-xs font-semibold text-text-muted">{message.author_id}</span>
                )}
                {message.content}
              </p>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        <form onSubmit={(event) => void send(event)} className="flex gap-2 border-t border-border p-3">
          <input
            value={text}
            onChange={(event) => setText(event.target.value)}
            disabled={!channelId}
            placeholder="Digite uma mensagem privada..."
            className="min-w-0 flex-1 rounded-md border border-border bg-bg px-3 py-2 text-sm text-text disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={!channelId || !text.trim()}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            Enviar
          </button>
        </form>
      </section>
    </div>
  );
}
