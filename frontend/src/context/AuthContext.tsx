import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from "react";
import { api, ApiError, getToken, setToken, UNAUTHORIZED_EVENT } from "../services/api";
import type { User } from "../types";

interface AuthState {
  user: User | null;
  initializing: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  /** Adopt an already-issued session (one-click demo account). */
  setSessionFromPayload: (payload: { token: string; user: User }) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(true);

  const loadUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setInitializing(false);
      return;
    }
    try {
      const data = await api.get<{ user: User }>("/auth/me");
      setUser(data.user);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setToken(null);
      setUser(null);
    } finally {
      setInitializing(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  // Any API 401 (token expired, revoked, or invalid) signs the session out
  // immediately so protected routes redirect to the sign-in page.
  useEffect(() => {
    const onUnauthorized = () => {
      setToken(null);
      setUser(null);
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.post<{ user: User; token: string }>("/auth/login", { email, password });
    setToken(data.token);
    setUser(data.user);
  }, []);

  const register = useCallback(async (name: string, email: string, password: string) => {
    const data = await api.post<{ user: User; token: string }>("/auth/register", { name, email, password });
    setToken(data.token);
    setUser(data.user);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const data = await api.get<{ user: User }>("/auth/me");
    setUser(data.user);
  }, []);

  const setSessionFromPayload = useCallback((payload: { token: string; user: User }) => {
    setToken(payload.token);
    setUser(payload.user);
  }, []);

  const value = useMemo(
    () => ({ user, initializing, login, register, logout, refreshUser, setSessionFromPayload }),
    [user, initializing, login, register, logout, refreshUser, setSessionFromPayload],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}