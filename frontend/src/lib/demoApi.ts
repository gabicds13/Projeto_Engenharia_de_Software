/**
 * API inteiramente local para capturas de telas quando o Módulo 1 estiver
 * indisponível. NÃO envia requisições, NÃO autentica usuários reais e NÃO
 * lê ou grava dados em Azure/Neon. Conteúdo fictício e volátil.
 */
import type {
  ChatMessage,
  CodeReviewsResponse,
  DashboardResponse,
  Notification,
  Priority,
  Source,
} from "./types";

const PROJECT_ID = "projeto-demo-modulo6";
const PROJECT_2 = "projeto-demo-exemplo";
const DEMO_USER = "usuario-demo";
const stamp = (offsetDays = 0) => new Date(Date.now() - offsetDays * 86400_000).toISOString();
const projects = [
  { id: PROJECT_ID, project_id: PROJECT_ID, name: "Projeto Módulo 6 (demonstração)" },
  { id: PROJECT_2, project_id: PROJECT_2, name: "Projeto Exemplo (demonstração)" },
];

function note(id: string, source: Source, priority: Priority, title: string, body: string, days: number): Notification {
  return {
    id, source, type: "evento.demo", priority, relevance_score: priority === "critical" ? 0.95 : priority === "high" ? 0.85 : 0.68,
    reason: "Classificação ilustrativa por regras.", classified_by: "rules",
    project_id: PROJECT_ID, title, body, link: null, created_at: stamp(days), read_at: null,
    summary: "Exemplo de notificação gerada localmente para demonstração.", group_key: source,
  };
}

let notifications: Notification[] = [
  note("demo-1", "code_review", "critical", "Revisão de código solicitada", "Exemplo: pull request aguardando análise no projeto.", 0),
  note("demo-2", "github", "high", "Novo pull request aberto", "Exemplo: atualização do frontend enviada para revisão.", 0),
  note("demo-3", "backlog", "medium", "História atualizada", "Exemplo: uma user story foi movida para Em andamento.", 1),
  note("demo-4", "chat", "low", "Mensagem da equipe", "Exemplo: nova atualização no chat geral do projeto.", 2),
];
let generalMessages: ChatMessage[] = [
  { id: "chat-demo-1", project_id: PROJECT_ID, author_id: "integrante-demo", content: "Pessoal, vamos revisar o Dashboard do Módulo 6?", created_at: stamp(1) },
  { id: "chat-demo-2", project_id: PROJECT_ID, author_id: DEMO_USER, content: "Claro! Já organizei as métricas e as notificações.", created_at: stamp(0.8) },
  { id: "chat-demo-3", project_id: PROJECT_ID, author_id: "integrante-demo", content: "Ótimo, depois conferimos as capturas das telas.", created_at: stamp(0.4) },
];

interface DirectChannel {
  id: string; project_id: string; type: string; member_ids: string[];
  created_at: string; pending: boolean; needs_my_acceptance: boolean;
}
interface DirectMessage {
  id: string; channel_id: string; project_id: string;
  author_id: string; content: string; created_at: string;
}
let directChannels: DirectChannel[] = [{
  id: "canal-demo-1", project_id: PROJECT_ID, type: "direct",
  member_ids: [DEMO_USER, "integrante-demo"], created_at: stamp(2),
  pending: false, needs_my_acceptance: false,
}];
let directMessages: DirectMessage[] = [
  { id: "privado-demo-1", channel_id: "canal-demo-1", project_id: PROJECT_ID, author_id: "integrante-demo", content: "Você consegue mostrar a tela das notificações?", created_at: stamp(0.5) },
  { id: "privado-demo-2", channel_id: "canal-demo-1", project_id: PROJECT_ID, author_id: DEMO_USER, content: "Sim, já preparei a demonstração.", created_at: stamp(0.3) },
];
let seq = 10;

function dashboard(projectId: string): DashboardResponse {
  return {
    project_id: projectId,
    cards: [
      { key: "commits_week", state: "ok", stale: false, data_origin: "mock", value: 24 },
      { key: "open_prs", state: "ok", stale: false, data_origin: "mock", value: 3 },
      { key: "reviews_pending", state: "unavailable", stale: false, data_origin: "mock", value: null },
      { key: "stories_by_status", state: "ok", stale: false, data_origin: "mock", value: { todo: 8, in_progress: 4, in_review: 2, done: 10 } },
    ],
    weekly: { key: "weekly", state: "ok", stale: false, data_origin: "mock",
      value: { points: [
        { week: "Sem. 1", commits: 11, prs: 2 },
        { week: "Sem. 2", commits: 18, prs: 3 },
        { week: "Sem. 3", commits: 14, prs: 2 },
        { week: "Sem. 4", commits: 22, prs: 4 },
        { week: "Sem. 5", commits: 19, prs: 3 },
        { week: "Sem. 6", commits: 24, prs: 3 },
      ] },
    },
    mackai: { state: "disabled", metrics: null },
  };
}

function codeReviews(projectId: string): CodeReviewsResponse {
  return {
    project_id: projectId, source: "module-4", history_limited: true, pending_reviews: null,
    items: [{
      id: "review-exemplo-local", reviewed_at: stamp(1),
      pr_url: "https://github.com/gabicds13/Projeto_Engenharia_de_Software/pull/23",
      architecture: "Microsserviços", findings_count: 2,
      severity_counts: { Alta: 0, "Média": 1, Baixa: 1 },
    }],
  };
}

function clone<T>(value: T): T {
  return value === undefined ? value : JSON.parse(JSON.stringify(value)) as T;
}

/** Implementa apenas os contratos consumidos pelas telas do portal. */
export async function demoRequest<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const url = new URL(path, "http://demo.invalid");
  const pathname = url.pathname;
  const verb = method.toUpperCase();
  const out = (value: unknown): T => clone(value as T);

  if (pathname === "/api/bff/projects" && verb === "GET") return out(projects);
  if (pathname === "/api/bff/dashboard" && verb === "GET") return out(dashboard(url.searchParams.get("project_id") || PROJECT_ID));
  if (pathname === "/api/bff/code-reviews" && verb === "GET") return out(codeReviews(url.searchParams.get("project_id") || PROJECT_ID));

  if (pathname === "/api/bff/notifications" && verb === "GET") {
    return out({ state: "ok", stale: false, page: { items: notifications, next_cursor: null } });
  }
  if (pathname === "/api/bff/notifications/unread-count" && verb === "GET") {
    const pending = notifications.filter(n => !n.read_at);
    return out({
      state: "ok", stale: false,
      count: { total: pending.length, critical: pending.filter(n => n.priority === "critical").length,
        high: pending.filter(n => n.priority === "high").length,
        medium: pending.filter(n => n.priority === "medium").length,
        low: pending.filter(n => n.priority === "low").length },
    });
  }
  if (pathname === "/api/bff/notifications/read-all" && verb === "POST") {
    notifications = notifications.map(n => ({ ...n, read_at: n.read_at ?? new Date().toISOString() }));
    return out(undefined);
  }
  const readMatch = pathname.match(/^\/api\/bff\/notifications\/([^/]+)$/);
  if (readMatch && verb === "PATCH") {
    notifications = notifications.map(n => n.id === readMatch[1] ? { ...n, read_at: new Date().toISOString() } : n);
    return out(undefined);
  }

  const directMatch = pathname.match(/^\/api\/bff\/chat\/rooms\/([^/]+)\/direct(?:\/([^/]+))?(?:\/(messages|read|unread|accept))?$/);
  if (directMatch) {
    const projectId = decodeURIComponent(directMatch[1]);
    const channelId = directMatch[2] ? decodeURIComponent(directMatch[2]) : null;
    const action = directMatch[3];
    if (!channelId && verb === "GET") return out(directChannels.filter(c => c.project_id === projectId));
    if (!channelId && verb === "POST") {
      const target = String((body as { target_user_id?: string })?.target_user_id ?? "integrante-demo");
      const newChannel: DirectChannel = {
        id: "canal-demo-" + ++seq, project_id: projectId, type: "direct",
        member_ids: [DEMO_USER, target], created_at: new Date().toISOString(),
        pending: false, needs_my_acceptance: false,
      };
      directChannels = [...directChannels, newChannel];
      return out({ id: newChannel.id });
    }
    if (channelId && action === "messages" && verb === "GET") return out(directMessages.filter(m => m.channel_id === channelId));
    if (channelId && action === "messages" && verb === "POST") {
      const message: DirectMessage = {
        id: "privado-demo-" + ++seq, channel_id: channelId, project_id: projectId,
        author_id: DEMO_USER, content: String((body as { content?: string })?.content ?? ""),
        created_at: new Date().toISOString(),
      };
      directMessages = [...directMessages, message];
      return out(message);
    }
    if (channelId && action === "unread" && verb === "GET") return out({ unread: 0 });
    if (channelId && action === "read" && verb === "POST") return out(undefined);
    if (channelId && action === "accept" && verb === "POST") {
      directChannels = directChannels.map(c => c.id === channelId ? { ...c, pending: false, needs_my_acceptance: false } : c);
      return out(undefined);
    }
  }

  const chatMatch = pathname.match(/^\/api\/bff\/chat\/rooms\/([^/]+)\/(unread|messages|read)$/);
  if (chatMatch) {
    const projectId = decodeURIComponent(chatMatch[1]);
    const action = chatMatch[2];
    if (action === "unread" && verb === "GET") return out({ project_id: projectId, unread: 0 });
    if (action === "read" && verb === "POST") return out(undefined);
    if (action === "messages" && verb === "GET") return out({ state: "ok", stale: false, project_id: projectId, messages: generalMessages.filter(m => m.project_id === projectId) });
    if (action === "messages" && verb === "POST") {
      const message: ChatMessage = {
        id: "chat-demo-" + ++seq, project_id: projectId, author_id: DEMO_USER,
        content: String((body as { content?: string })?.content ?? ""), created_at: new Date().toISOString(),
      };
      generalMessages = [...generalMessages, message];
      return out(message);
    }
  }

  throw new Error("Rota não implementada no modo demonstração: " + verb + " " + pathname);
}
