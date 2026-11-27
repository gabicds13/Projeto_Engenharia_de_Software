import { useEffect, useState } from "react";
import { api } from "../../lib/apiClient";
import type { CodeReviewMetrics, CodeReviewMetricsResponse, CodeReviewMetricsScope, Priority } from "../../lib/types";

const PERIODS = [7, 14, 30, 60, 90] as const;
const PRIORITIES: { key: Priority; label: string; color: string }[] = [
  { key: "critical", label: "Crítica", color: "var(--color-priority-critical)" },
  { key: "high", label: "Alta", color: "var(--color-priority-high)" },
  { key: "medium", label: "Média", color: "var(--color-priority-medium)" },
  { key: "low", label: "Baixa", color: "var(--color-priority-low)" },
];
type BarItem = { label: string; value: number; color: string };

function countBars(group: Record<string, number>, color: string): BarItem[] {
  return Object.entries(group)
    .sort((a, b) => b[1] - a[1])
    .map(([label, value]) => ({ label, value, color }));
}

function Distribution({ title, items }: { title: string; items: BarItem[] }) {
  const max = Math.max(1, ...items.map((item) => item.value));
  return (
    <figure className="min-w-0 rounded-lg border border-border p-4">
      <figcaption className="mb-4 text-sm font-semibold text-text">{title}</figcaption>
      {items.length === 0 ? (
        <p className="text-sm text-text-muted">Sem registros no período.</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.label}>
              <div className="flex items-baseline justify-between gap-2 text-xs">
                <span className="min-w-0 break-words text-text">{item.label}</span>
                <span className="metric text-text">{item.value}</span>
              </div>
              <div className="mt-1 h-2 rounded bg-bg" aria-hidden="true">
                <div className="h-full rounded" style={{ width: (item.value / max) * 100 + "%", backgroundColor: item.color }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </figure>
  );
}

function DailyChart({ rows }: { rows: CodeReviewMetrics["revisoes_por_dia"] }) {
  const max = Math.max(1, ...rows.flatMap((row) => [row.revisoes, row.achados]));
  return (
    <figure className="min-w-0 rounded-lg border border-border p-4">
      <figcaption className="mb-3 text-sm font-semibold text-text">Revisões e achados por dia</figcaption>
      {rows.length === 0 ? <p className="text-sm text-text-muted">Sem registros no período.</p> : (
        <>
          <div className="mb-3 flex flex-wrap gap-3 text-xs text-text-muted">
            <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: "var(--chart-1)" }} />Revisões</span>
            <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: "var(--chart-2)" }} />Achados</span>
          </div>
          <div className="overflow-x-auto">
            <div className="flex min-w-max items-end gap-2 border-b border-border" style={{ minWidth: Math.max(0, rows.length * 44) }}>
              {rows.map((row) => (
                <div key={row.data} className="flex min-w-9 flex-1 flex-col items-center" title={row.data + ": " + row.revisoes + " revisões, " + row.achados + " achados"}>
                  <div className="flex h-36 w-full items-end justify-center gap-1" aria-hidden="true">
                    <div className="w-3 rounded-t" style={{ height: row.revisoes / max * 100 + "%", backgroundColor: "var(--chart-1)" }} />
                    <div className="w-3 rounded-t" style={{ height: row.achados / max * 100 + "%", backgroundColor: "var(--chart-2)" }} />
                  </div>
                  <span className="mt-1 text-[10px] text-text-muted">{row.data.slice(8, 10)}/{row.data.slice(5, 7)}</span>
                </div>
              ))}
            </div>
          </div>
          <details className="mt-3 text-xs text-text-muted">
            <summary className="cursor-pointer">Ver valores por dia</summary>
            <table className="mt-2 w-full text-left">
              <thead><tr><th>Data</th><th>Revisões</th><th>Achados</th></tr></thead>
              <tbody>{rows.map(row => <tr key={row.data}><td>{row.data}</td><td>{row.revisoes}</td><td>{row.achados}</td></tr>)}</tbody>
            </table>
          </details>
        </>
      )}
    </figure>
  );
}

export function CodeReviewMetricsPanel({ projectId }: { projectId: string }) {
  const [scope, setScope] = useState<CodeReviewMetricsScope>("project");
  const [days, setDays] = useState<number>(14);
  const [refresh, setRefresh] = useState(0);
  const [result, setResult] = useState<CodeReviewMetricsResponse | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "unavailable">("loading");

  useEffect(() => {
    let active = true;
    setResult(null);
    setState("loading");
    const expectedProject = scope === "project" ? projectId : null;
    const query = scope === "project"
      ? new URLSearchParams({ project_id: projectId, dias: String(days) })
      : new URLSearchParams({ dias: String(days) });
    const endpoint = scope === "global" ? "/api/bff/code-reviews/metrics/global" : "/api/bff/code-reviews/metrics";
    async function load() {
      try {
        const response = await api.get<CodeReviewMetricsResponse>(endpoint + "?" + query);
        if (!active) return;
        if (response.scope !== scope || response.project_id !== expectedProject || response.dias !== days ||
            response.source !== "module-4" || response.data_origin !== "real" || !response.metrics) {
          throw new Error("Contrato de métricas inválido");
        }
        setResult(response);
        setState("ok");
      } catch {
        if (active) {
          setResult(null);
          setState("unavailable");
        }
      }
    }
    void load();
    return () => { active = false; };
  }, [projectId, days, scope, refresh]);

  const metrics = state === "ok" && result?.scope === scope &&
    result.project_id === (scope === "project" ? projectId : null) && result.dias === days ? result.metrics : null;
  return (
    <section className="rounded-lg border border-border bg-surface p-4" aria-label="Métricas de Code Review - Módulo 4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-text">Métricas de Code Review — Módulo 4</h2>
          <p className="text-xs text-text-muted">
            {scope === "global"
              ? "Dados globais de todos os projetos publicados pelo Módulo 4."
              : "Revisões realizadas e achados do projeto selecionado."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-sm text-text">
            Período
            <select value={days} onChange={event => setDays(Number(event.target.value))}
              className="ml-2 rounded-md border border-border bg-bg px-2 py-2 text-sm text-text">
              {PERIODS.map(value => <option key={value} value={value}>{value} dias</option>)}
            </select>
          </label>
          <button type="button" onClick={() => setRefresh(value => value + 1)} disabled={state === "loading"}
            className="rounded-md border border-border px-3 py-2 text-sm text-text disabled:opacity-50">
            Atualizar métricas
          </button>
        </div>
      </div>
      <div role="group" aria-label="Escopo das métricas de Code Review" className="mb-4 flex flex-wrap gap-2">
        {([
          { value: "project", label: "Projeto selecionado" },
          { value: "global", label: "Todos os projetos" },
        ] as const).map(option => (
          <button key={option.value} type="button" aria-pressed={scope === option.value}
            onClick={() => setScope(option.value)}
            className={scope === option.value
              ? "rounded-md bg-primary px-3 py-2 text-sm font-medium text-white"
              : "rounded-md border border-border px-3 py-2 text-sm text-text"}>
            {option.label}
          </button>
        ))}
      </div>
      {scope === "global" && (
        <p className="mb-4 rounded-md border border-border bg-bg p-3 text-xs text-text-muted">
          Visão global: estes números não representam exclusivamente o projeto selecionado.
          O histórico de PRs e as demais métricas do Dashboard continuam filtrados por projeto.
        </p>
      )}
      {state === "loading" && <p className="text-sm text-text-muted">Consultando métricas do Módulo 4…</p>}
      {state === "unavailable" && <p role="status" className="text-sm text-text-muted">Métricas de Code Review indisponíveis no momento. As outras áreas continuam funcionando.</p>}
      {metrics && (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[
              { label: "Revisões realizadas", value: metrics.total_revisoes },
              { label: "Total de achados", value: metrics.total_achados },
              { label: "Achados críticos", value: metrics.por_prioridade.critical ?? 0 },
              { label: "Achados altos", value: metrics.por_prioridade.high ?? 0 },
            ].map(item => <div key={item.label} className="rounded-md border border-border p-3">
              <p className="text-xs text-text-muted">{item.label}</p>
              <p className="metric mt-1 text-xl font-semibold text-text">{item.value}</p>
            </div>)}
          </div>
          {metrics.total_revisoes === 0 && metrics.total_achados === 0 && (
            <p className="mb-4 rounded-md border border-border bg-bg p-3 text-sm text-text-muted">
              {scope === "project"
                ? "Nenhuma revisão ou achado registrado pelo Módulo 4 para este projeto no período. Consulte Todos os projetos para visualizar as contagens globais."
                : "Nenhuma revisão ou achado global registrado no período."}
            </p>
          )}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Distribution title="Achados por prioridade" items={PRIORITIES.map(item => ({ label: item.label, color: item.color, value: metrics.por_prioridade[item.key] ?? 0 }))} />
            <DailyChart rows={metrics.revisoes_por_dia} />
            <Distribution title="Achados por categoria" items={countBars(metrics.por_categoria, "var(--chart-3)")} />
            <Distribution title="Estilos de arquitetura analisados" items={countBars(metrics.por_arquitetura, "var(--chart-4)")} />
          </div>
        </>
      )}
    </section>
  );
}
