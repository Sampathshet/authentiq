import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  api,
  clearAuthSession,
  getAccessToken,
  getStoredUser,
  setAuthSession,
  setSessionExpiredHandler,
  setStoredUser,
} from "@/lib/api";
import type { AuthResponse, User } from "@/lib/types";

interface LoginPayload {
  email: string;
  password: string;
  remember_me: boolean;
}

interface RegisterPayload {
  display_name: string;
  email: string;
  password: string;
  confirm_password: string;
  account_type: "individual" | "organization";
  organization_name?: string;
  accept_terms: boolean;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (payload: LoginPayload) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User | null>;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => getStoredUser<User>());
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const updateUser = useCallback((next: User) => {
    setUser(next);
    setStoredUser(next);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      return null;
    }
    try {
      const next = await api.get<User>("/auth/me");
      updateUser(next);
      return next;
    } catch {
      return null;
    }
  }, [updateUser]);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      setUser(null);
      navigate("/login", { replace: true, state: { reason: "Your session expired. Sign in to continue." } });
    });
    const token = getAccessToken();
    if (!token) {
      setLoading(false);
      return;
    }
    refreshUser().finally(() => setLoading(false));
  }, [navigate, refreshUser]);

  const login = useCallback(
    async (payload: LoginPayload) => {
      const response = await api.post<AuthResponse>("/auth/login", payload);
      setAuthSession(response.access_token, response.refresh_token, response.user);
      setUser(response.user);
      return response.user;
    },
    [],
  );

  const register = useCallback(async (payload: RegisterPayload) => {
    const response = await api.post<AuthResponse>("/auth/register", payload);
    setAuthSession(response.access_token, response.refresh_token, response.user);
    setUser(response.user);
    return response.user;
  }, []);

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem("authentiq_refresh_token");
    try {
      await api.post("/auth/logout", refresh ? { refresh_token: refresh } : undefined);
    } catch {
      clearAuthSession();
    } finally {
      clearAuthSession();
      setUser(null);
      navigate("/login", { replace: true });
    }
  }, [navigate]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, login, register, logout, refreshUser, updateUser }),
    [user, loading, login, register, logout, refreshUser, updateUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
