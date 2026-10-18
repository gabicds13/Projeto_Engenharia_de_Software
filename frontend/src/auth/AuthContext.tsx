import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, getToken, setToken, setUnauthorizedHandler } from "../lib/apiClient";
import type { Role } from "../lib/types";

interface SessionUser {
  user_id: string;
  role: Role;
  project_ids: string[];
}

interface AuthState {
  user: SessionUser | null;
  token: string | null;
  loginWithToken: (token: string) => void;
  loginDev: (profile: "po" | "pm" | "dev") => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

// Decodifica o payload do JWT (sem validar assinatura — a validação é no BFF).
function decode(token: string): SessionUser | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return {
      user_id: payload.sub ?? payload.user_id,
      role: payload.role,
      project_ids: payload.project_ids ?? [],
    };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const user = useMemo(() => (token ? decode(token) : null), [token]);

  const loginWithToken = useCallback((t: string) => {
    setToken(t);
    setTokenState(t);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setTokenState(null);
  }, []);

  const loginDev = useCallback(
    async (profile: "po" | "pm" | "dev") => {
      const tokens = await api.get<Record<string, string>>("/api/bff/dev/tokens");
      loginWithToken(tokens[profile]);
    },
    [loginWithToken],
  );

  useEffect(() => {
    setUnauthorizedHandler(() => setTokenState(null));
  }, []);

  const value = useMemo(
    () => ({ user, token, loginWithToken, loginDev, logout }),
    [user, token, loginWithToken, loginDev, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de AuthProvider");
  return ctx;
}
