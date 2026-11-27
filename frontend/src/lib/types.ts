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
  personal_relevance_score?: number | null;
  personal_reason?: string | null;
  personalization_preview?: boolean;
  reason: string;
  classified_by: "llm" | "rules";
  summary?: string | null;
  group_key?: string | null;
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
  data_origin?: "real" | "mock";
  value: unknown;
}

export interface MackaiMetrics {
  project_id: string;
  conversations: number;
  users: number;
  questions: number;
  answers_up: number;
  answers_down: number;
  answers_not_grounded: number;
  last_question_at: string | null;
}

export interface MackaiMetricsResult {
  state: "ok" | "unavailable" | "disabled";
  metrics: MackaiMetrics | null;
}

export interface CodeReviewSummary {
  id: string;
  reviewed_at: string;
  pr_url: string;
  architecture: string;
  findings_count: number;
  severity_counts: Record<string, number>;
}

export interface CodeReviewsResponse {
  project_id: string;
  source: "module-4";
  history_limited: true;
  pending_reviews: null;
  items: CodeReviewSummary[];
}

export interface DashboardResponse {
  project_id: string;
  cards: DashboardCard[];
  weekly: DashboardCard;
  mackai?: MackaiMetricsResult;
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


export interface CodeReviewMetrics {
  total_revisoes: number;
  total_achados: number;
  por_prioridade: Partial<Record<Priority, number>>;
  por_categoria: Record<string, number>;
  por_arquitetura: Record<string, number>;
  revisoes_por_dia: { data: string; revisoes: number; achados: number }[];
}

export type CodeReviewMetricsScope = "project" | "global";

export interface CodeReviewMetricsResponse {
  project_id: string | null;
  scope: CodeReviewMetricsScope;
  dias: number;
  source: "module-4";
  data_origin: "real";
  metrics: CodeReviewMetrics;
}
