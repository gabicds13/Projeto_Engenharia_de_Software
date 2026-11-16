import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/apiClient";
import type { CuradoriaEmAltaResponse } from "../../lib/types";

type Status = "loading" | "ok" | "unavailable";

export function CuradoriaPanel() {
  const [status, setStatus] = useState<Status>("loading");
  const [result, setResult] = useState<CuradoriaEmAltaResponse | null>(null);

  const load = useCallback(async (isActive: () => boolean = () => true) => {
    setStatus("loading");
    try {
      const response = await api.get<CuradoriaEmAltaResponse>("/api/bff/curadoria/em-alta");
      if (!isActive()) return;
      if (
        response.source !== "module-5" ||
        response.scope !== "global" ||
        !Array.isArray(response.articles)
      ) {
        throw new Error("Formato do feed inválido");
      }
      setResult(response);
      setStatus("ok");
    } catch {
      if (!isActive()) return;
      setResult(null);
      setStatus("unavailable");
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    void load(() => mounted);
    return () => { mounted = false; };
  }, [load]);

  return (
    <section aria-label="Tendências tecnológicas - Módulo 5"
      className="rounded-lg border border-border bg-surface p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-text">Tendências tecnológicas — Módulo 5</h2>
        <button type="button" disabled={status === "loading"} onClick={() => void load()}
          className="rounded-md border border-border px-3 py-2 text-sm text-text disabled:opacity-50">
          Atualizar tendências
        </button>
      </div>
      <p className="mb-3 text-xs text-text-muted">
        Artigos em alta na tecnologia, selecionados pelo Módulo 5. Feed geral,
        não específico deste projeto.
      </p>
      {status === "loading" && (
        <p className="text-sm text-text-muted">Carregando tendências…</p>
      )}
      {status === "unavailable" && (
        <p role="status" className="text-sm text-text-muted">
          Tendências indisponíveis no momento ou integração ainda não ativada.
          O restante do Dashboard continua funcionando.
        </p>
      )}
      {status === "ok" && result && (
        result.articles.length === 0 ? (
          <p className="text-sm text-text-muted">Nenhum artigo disponível no feed do Módulo 5.</p>
        ) : (
          <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {result.articles.map((article) => (
              <li key={article.url} className="rounded-md border border-border p-3">
                <a href={article.url} target="_blank" rel="noopener noreferrer"
                  className="text-sm font-medium text-primary underline">
                  {article.title}
                </a>
                <p className="mt-2 text-xs text-text-muted">
                  {article.source} · {article.category}
                </p>
              </li>
            ))}
          </ul>
        )
      )}
    </section>
  );
}
