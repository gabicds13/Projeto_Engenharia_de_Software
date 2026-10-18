import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { WeeklyPoint } from "../../lib/types";

// Lê as cores dos tokens (CSS variables) em runtime, respeitando o tema atual.
function cssVar(name: string): string {
  if (typeof window === "undefined") return "#000";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export function WeeklyChart({ points }: { points: WeeklyPoint[] }) {
  const chart1 = cssVar("--chart-1");
  const chart2 = cssVar("--chart-2");
  const muted = cssVar("--color-text-muted");

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={cssVar("--color-border")} />
          <XAxis dataKey="week" tick={{ fill: muted, fontSize: 12 }} />
          <YAxis tick={{ fill: muted, fontSize: 12 }} allowDecimals={false} />
          <Tooltip
            contentStyle={{
              background: cssVar("--color-surface"),
              border: `1px solid ${cssVar("--color-border")}`,
              color: cssVar("--color-text"),
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: muted }} />
          <Bar dataKey="commits" name="Commits" fill={chart1} radius={[4, 4, 0, 0]} />
          <Bar dataKey="prs" name="PRs" fill={chart2} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
