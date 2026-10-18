// Resolve a URL base do BFF.
//
// - Em desenvolvimento (Vite) e no docker-compose local, deixamos VAZIO: o front
//   usa caminhos relativos (/api, /ws) e o proxy do Vite/nginx encaminha ao BFF.
// - Na nuvem, o portal e o BFF ficam em domínios diferentes. Defina
//   VITE_API_BASE_URL (em tempo de BUILD) com a URL pública do BFF, ex.:
//   https://ms-dashboard-bff.onrender.com
const RAW_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").trim().replace(/\/$/, "");

// URL base para chamadas REST (http/https). Vazia => relativa à origem do portal.
export const API_BASE_URL = RAW_BASE;

/** Monta a URL REST completa a partir de um caminho iniciado por "/". */
export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

/** Monta a URL de WebSocket completa a partir de um caminho iniciado por "/". */
export function wsUrl(path: string): string {
  if (RAW_BASE) {
    // Converte http(s):// -> ws(s)://
    const base = RAW_BASE.replace(/^http/, "ws");
    return `${base}${path}`;
  }
  // Sem base configurada: usa a origem atual do portal.
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}
