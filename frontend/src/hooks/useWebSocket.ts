import { useEffect, useRef, useState } from "react";

type Status = "connecting" | "open" | "closed";

interface Options {
  // Chamado a cada mensagem JSON recebida.
  onMessage: (data: unknown) => void;
  // Chamado quando (re)conecta, para o consumidor recuperar o que perdeu via REST.
  onReconnect?: () => void;
  enabled?: boolean;
}

const MAX_BACKOFF_MS = 15_000;

/**
 * Conecta a um WebSocket do BFF com reconexão por backoff exponencial + jitter.
 * Ao (re)abrir, dispara onReconnect para o consumidor buscar o estado atual via REST
 * (recuperação sem duplicatas — a idempotência fica no ms-notifications).
 */
export function useWebSocket(url: string | null, opts: Options): Status {
  const { onMessage, onReconnect, enabled = true } = opts;
  const [status, setStatus] = useState<Status>("closed");
  const attemptRef = useRef(0);
  const msgRef = useRef(onMessage);
  const reconnectRef = useRef(onReconnect);
  msgRef.current = onMessage;
  reconnectRef.current = onReconnect;

  useEffect(() => {
    if (!url || !enabled) return;

    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let closedByUs = false;

    const connect = () => {
      setStatus("connecting");
      ws = new WebSocket(toAbsolute(url));

      ws.onopen = () => {
        attemptRef.current = 0;
        setStatus("open");
        reconnectRef.current?.();
      };

      ws.onmessage = (ev) => {
        try {
          msgRef.current(JSON.parse(ev.data));
        } catch {
          /* ignora frames não-JSON (ex.: ping textual) */
        }
      };

      ws.onclose = () => {
        setStatus("closed");
        if (closedByUs) return;
        const attempt = (attemptRef.current += 1);
        const base = Math.min(MAX_BACKOFF_MS, 500 * 2 ** attempt);
        const jitter = Math.random() * 0.3 * base;
        timer = setTimeout(connect, base + jitter);
      };

      ws.onerror = () => ws?.close();
    };

    connect();

    return () => {
      closedByUs = true;
      if (timer) clearTimeout(timer);
      ws?.close();
    };
  }, [url, enabled]);

  return status;
}

function toAbsolute(path: string): string {
  if (path.startsWith("ws://") || path.startsWith("wss://")) return path;
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}
