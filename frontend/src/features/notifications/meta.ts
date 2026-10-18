import type { Priority, Source } from "../../lib/types";

// A cor indica prioridade (classes de token Tailwind — nunca hex direto).
export const priorityBorder: Record<Priority, string> = {
  critical: "border-l-priority-critical",
  high: "border-l-priority-high",
  medium: "border-l-priority-medium",
  low: "border-l-priority-low",
};

export const priorityBadge: Record<Priority, string> = {
  critical: "bg-priority-critical text-white",
  high: "bg-priority-high text-white",
  medium: "bg-priority-medium text-white",
  low: "bg-priority-low text-white",
};

export const priorityLabel: Record<Priority, string> = {
  critical: "CRÍTICA",
  high: "ALTA",
  medium: "MÉDIA",
  low: "BAIXA",
};

// O ícone + rótulo indicam a ORIGEM (nunca uma cor por módulo).
export const sourceMeta: Record<Source, { icon: string; label: string }> = {
  code_review: { icon: "⚙", label: "Code Review" },
  github: { icon: "⎇", label: "GitHub" },
  curadoria: { icon: "★", label: "Curadoria" },
  artefatos: { icon: "📄", label: "Artefatos" },
  rag: { icon: "💬", label: "Assistente" },
  relatorios: { icon: "📊", label: "Relatórios" },
  backlog: { icon: "🗂", label: "Backlog" },
  chat: { icon: "✉", label: "Chat" },
};

// Horário relativo em pt-BR, curto ("há 5 min", "há 2 h", "ontem").
export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diffMs = Date.now() - then;
  const min = Math.round(diffMs / 60000);
  if (min < 1) return "agora";
  if (min < 60) return `há ${min} min`;
  const hours = Math.round(min / 60);
  if (hours < 24) return `há ${hours} h`;
  const days = Math.round(hours / 24);
  if (days === 1) return "ontem";
  return `há ${days} dias`;
}
