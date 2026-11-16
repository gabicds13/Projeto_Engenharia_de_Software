import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/apiClient";
import type { CodeReviewsResponse } from "../../lib/types";

type LoadState = "loading" | "ok" | "unavailable";

function dateLabel(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? "Data não disponível"
    : date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function CodeReviewPanel({ projectId }: { projectId: string }) {
  const [state, setState] = useState<LoadState>("loading");
  const [data, setData] = useState<CodeReviewsResponse | null>(null);

  const reload = useCallback(async (isCurrent: () => boolean = () => true) => {
    setState("loading");
    try {
      const response = await api.get<CodeReviewsResponse>(
        `/api/bff/code-reviews?project_id=${encodeURIComponent(projectId)}`,
      );
      if (!isCurrent()) return;
      if (
        response.project_id !== projectId ||
        response.source !== "module-4" ||
        response.history_limited !== true ||
        !Array.isArray(response.items)
      ) {
        throw new Error("Contrato inválido do Módulo 4");
      }
      setData(response);
      setState("ok");
    } catch {
      if (!isCurrent()) return;
      // Nunca preservar dados antigos após uma falha de autorização/conexão.
      setData(null);
      setState("unavailable");
    }
  }, [projectId]);

  useEffect(() => {
    let active = true;
    const isCurrent = () => active;
    void reload(isCurrent);
    return () => { active = false; };
  }, [reload]);

  return (
    <section
      className="rounded-lg border border-border bg-surface p-4"
      aria-label="Revisões de código - Módulo 4"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-text">Revisões de código — Módulo 4</h2>
        <button
          type="button"
          onClick={() => void reload()}
          disabled={state === "loading"}
          className="rounded-md border border-border px-3 py-2 text-sm text-text disabled:opacity-50"
        >
          Atualizar revisões
        </button>
      </div>

      {state === "loading" && (
        <p className="text-sm text-text-muted">Consultando revisões do projeto…</p>
      )}
      {state === "unavailable" && (
        <p role="status" className="text-sm text-text-muted">
          Histórico de revisões indisponível ou integração ainda não ativada.
          O restante do Dashboard continua funcionando.
        </p>
      )}
      {state === "ok" && data && (
        <>
          <p className="mb-3 text-sm text-text-muted">
            Revisões encontradas neste projeto entre as 20 análises mais recentes do Módulo 4.
            Não representa o total de revisões nem os reviews pendentes.
          </p>
          {data.items.length === 0 ? (
            <p className="text-sm text-text-muted">
              Nenhuma revisão deste projeto encontrada nas últimas 20 análises.
            </p>
          ) : (
            <ul className="flex flex-col gap-3">
              {data.items.map((item) => (
                <li key={item.id} className="rounded-md border border-border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <a
                      href={item.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="break-all text-sm font-medium text-primary underline"
                    >
                      Ver Pull Request no GitHub
                    </a>
                    <span className="text-xs text-text-muted">{dateLabel(item.reviewed_at)}</span>
                  </div>
                  <p className="mt-2 text-sm text-text">
                    {item.findings_count} {item.findings_count === 1 ? "achado" : "achados"} na análise
                    {" · "}Arquitetura: {item.architecture}
                  </p>
                  <p className="mt-1 text-xs text-text-muted">
                    Alta: {item.severity_counts["Alta"] ?? 0}
                    {" · "}Média: {item.severity_counts["Média"] ?? 0}
                    {" · "}Baixa: {item.severity_counts["Baixa"] ?? 0}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
