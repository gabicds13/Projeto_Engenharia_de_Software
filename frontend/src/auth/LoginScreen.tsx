import { FormEvent, useState } from "react";
import { useAuth } from "./AuthContext";
import { ApiError } from "../lib/apiClient";

export function LoginScreen() {
  const { loginReal } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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