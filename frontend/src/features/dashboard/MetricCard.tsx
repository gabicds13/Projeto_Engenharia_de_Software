import type { ReactNode } from "react";

interface Props {
  label: string;
  state: "ok" | "unavailable";
  stale?: boolean;
  children?: ReactNode;
}

// Card de métrica. Números usam .metric (tabular-nums) para não "dançar".
export function MetricCard({ label, state, stale, children }: Props) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border bg-surface p-4">
      <span className="text-xs font-medium uppercase tracking-wide text-text-muted">
        {label}
      </span>
      {state === "unavailable" ? (
        <span className="text-sm text-text-muted">indisponível no momento</span>
      ) : (
        <>
          {children}
          {stale && (
            <span className="text-xs text-text-muted">dados do último cache</span>
          )}
        </>
      )}
    </div>
  );
}

export function MetricNumber({ value }: { value: number }) {
  return <span className="metric text-2xl font-semibold text-text">{value}</span>;
}
