import { useState } from "react";
import { useAuth } from "./AuthContext";

// Tela de login de desenvolvimento: gera tokens de teste via BFF para os 3 perfis.
export function LoginScreen() {
  const { loginDev } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);

  const entrar = async (perfil: "po" | "pm" | "dev") => {
    setError(null);
    setLoading(perfil);
    try {
      await loginDev(perfil);
    } catch {
      setError("Não foi possível obter o token de desenvolvimento. O BFF está no ar?");
    } finally {
      setLoading(null);
    }
  };

  return (
    <main className="flex min-h-full items-center justify-center bg-bg p-6">
      <div className="w-full max-w-md rounded-xl border border-border bg-surface p-8">
        <h1 className="text-xl font-semibold text-text">
          Módulo<span className="text-brand-accent">6</span> · Portal
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          Entre com um perfil de desenvolvimento para explorar o portal.
        </p>

        <div className="mt-6 flex flex-col gap-3">
          {(["po", "pm", "dev"] as const).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => entrar(p)}
              disabled={loading !== null}
              className="rounded-lg bg-primary px-4 py-3 text-md font-medium text-white transition-colors hover:bg-primary-hover disabled:opacity-60"
            >
              {loading === p ? "Entrando…" : `Entrar como ${label(p)}`}
            </button>
          ))}
        </div>

        {error && (
          <p className="mt-4 rounded-md border border-priority-critical/40 bg-priority-critical/10 p-3 text-sm text-text">
            {error}
          </p>
        )}
      </div>
    </main>
  );
}

function label(p: "po" | "pm" | "dev"): string {
  return { po: "Product Owner", pm: "Scrum Master", dev: "Desenvolvedor(a)" }[p];
}
