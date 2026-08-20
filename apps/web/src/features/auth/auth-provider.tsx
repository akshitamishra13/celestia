"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getCurrentUser, login as loginRequest, signup as signupRequest } from "@/lib/api/auth";
import { ApiError, getAccessToken, setAccessToken } from "@/lib/api/client";
import type { User } from "@/types/auth";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getAccessToken()) {
      setLoading(false);
      return;
    }

    getCurrentUser()
      .then((response) => setUser(response.data.user))
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) setAccessToken(null);
        else console.error("Unable to restore session.", error);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await loginRequest(email, password);
    if (!response.data.access_token) throw new Error("The server did not return an access token.");
    setAccessToken(response.data.access_token);
    setUser(response.data.user);
  }, []);

  const signup = useCallback(async (name: string, email: string, password: string) => {
    const response = await signupRequest(name, email, password);
    if (!response.data.access_token) throw new Error("The server did not return an access token.");
    setAccessToken(response.data.access_token);
    setUser(response.data.user);
  }, []);

  const logout = useCallback(async () => {
    setAccessToken(null);
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, login, signup, logout }), [user, loading, login, signup, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider.");
  return context;
}
