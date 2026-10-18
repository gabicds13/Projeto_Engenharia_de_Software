// Tipos espelhando os contratos do BFF (app/domain/schemas.py).

export type Priority = "critical" | "high" | "medium" | "low";

export type Source =
  | "code_review"
  | "github"
  | "curadoria"
  | "artefatos"
  | "rag"
  | "relatorios"
  | "backlog"
  | "chat";

export interface Notification {
  id: string;
  source: Source;
  type: string;
  priority: Priority;
  relevance_score: number;
  reason: string;
  classified_by: "llm" | "rules";
  project_id: string;
  title: string;
  body: string;
  link: string | null;
  created_at: string;
  read_at: string | null;
}

export interface NotificationPage {
  items: Notification[];
  next_cursor: string | null;
}

export interface ListResult {
  state: "ok" | "unavailable";
  stale: boolean;
  page: NotificationPage | null;
}

export interface UnreadCount {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface UnreadResult {
  state: "ok" | "unavailable";
  stale: boolean;
  count: UnreadCount | null;
}

export interface StoriesByStatus {
  todo: number;
  in_progress: number;
  in_review: number;
  done: number;
}

export interface WeeklyPoint {
  week: string;
  commits: number;
  prs: number;
}

export interface DashboardCard {
  key: string;
  state: "ok" | "unavailable";
  stale: boolean;
  value: unknown;
}

export interface DashboardResponse {
  project_id: string;
  cards: DashboardCard[];
  weekly: DashboardCard;
}

export interface ChatMessage {
  id: string;
  project_id: string;
  author_id: string;
  content: string;
  created_at: string;
}

export interface ChatHistoryResult {
  state: "ok" | "unavailable";
  stale: boolean;
  project_id: string;
  messages: ChatMessage[];
}

export type Role = "PO" | "PM" | "DEV";
