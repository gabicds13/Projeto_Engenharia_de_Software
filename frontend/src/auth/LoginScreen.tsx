import { FormEvent, useState } from "react";
import { useAuth } from "./AuthContext";
import { ApiError } from "../lib/apiClient";
import { MODULE1_OFFLINE } from "../lib/offlineModule1";

export function LoginScreen() {
  const { loginReal, loginDev } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const entrarLocal = async () => {
    setError(null);
    setLoading(true);
    try {
      // O backend real em development emite e valida um JWT assinado.
      await loginDev("pm");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "O backend local nao respondeu. Inicie o BFF.");
    } finally {
      setLoading(false);
    }
  };

  const entrar = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setError(null);
    setLoading(true);

    try {
      await loginReal(email, password);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Não foi possível realizar o login.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (MODULE1_OFFLINE) {
    return (
      <main className="flex min-h-full items-center justify-center bg-bg p-6">
        <div className="w-full max-w-md rounded-xl border border-border bg-surface p-8">
          <h1 className="text-xl font-semibold text-text">Módulo<span className="text-brand-accent">6</span> · Portal</h1>
          <p className="mt-2 text-sm text-text-muted">Ambiente local conectado ao backend real do Módulo 6.</p>
          <p className="mt-4 rounded-md border border-border p-3 text-sm text-text">
            Login e projetos do Módulo 1 substituídos por dados de desenvolvimento.
            Dashboard, notificações e chat acessam o nosso backend. Recursos que dependem
            de tokens reais de outros módulos podem continuar indisponíveis.
          </p>
          <button type="button" onClick={() => void entrarLocal()} disabled={loading}
            className="mt-5 w-full rounded-lg bg-primary px-4 py-3 font-medium text-white hover:bg-primary-hover disabled:opacity-60">
            {loading ? "Conectando ao backend..." : "Entrar com backend local"}
          </button>
          {error && <p role="alert" className="mt-3 text-sm text-text">{error}</p>}
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-full items-center justify-center bg-bg p-6">
      <div className="w-full max-w-md rounded-xl border border-border bg-surface p-8">
        <h1 className="text-xl font-semibold text-text">
          Módulo<span className="text-brand-accent">6</span> · Portal
        </h1>

        <p className="mt-1 text-sm text-text-muted">
          Entre com sua conta do Módulo 1 para acessar o portal.
        </p>

        <form onSubmit={entrar} className="mt-6 flex flex-col gap-4">
          <div>
            <label
              htmlFor="email"
              className="mb-1 block text-sm font-medium text-text"
            >
              E-mail
            </label>

            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoComplete="email"
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-text outline-none focus:border-primary"
              placeholder="seu@email.com"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1 block text-sm font-medium text-text"
            >
              Senha
            </label>

            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              autoComplete="current-password"
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-text outline-none focus:border-primary"
              placeholder="Sua senha"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-primary px-4 py-3 text-md font-medium text-white transition-colors hover:bg-primary-hover disabled:opacity-60"
          >
            {loading ? "Entrando…" : "Entrar"}
          </button>
        </form>

        {error && (
          <p className="mt-4 rounded-md border border-priority-critical/40 bg-priority-critical/10 p-3 text-sm text-text">
            {error}
          </p>
        )}
      </div>
    </main>
  );
}