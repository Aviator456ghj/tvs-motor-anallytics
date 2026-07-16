"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api } from "./api";
import { User, UserRole } from "./types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string; role: UserRole; city?: string; phone?: string }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function fetchMe() {
    try {
      const me = await api.get<User>("/auth/me");
      setUser(me);
    } catch {
      setUser(null);
      localStorage.removeItem("servicesos_token");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (localStorage.getItem("servicesos_token")) {
      fetchMe();
    } else {
      setLoading(false);
    }
  }, []);

  async function login(email: string, password: string) {
    const res = await api.post<{ access_token: string }>("/auth/login", { email, password });
    localStorage.setItem("servicesos_token", res.access_token);
    await fetchMe();
  }

  async function register(data: { email: string; password: string; full_name: string; role: UserRole; city?: string; phone?: string }) {
    const res = await api.post<{ access_token: string }>("/auth/register", data);
    localStorage.setItem("servicesos_token", res.access_token);
    await fetchMe();
  }

  function logout() {
    localStorage.removeItem("servicesos_token");
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function useRequireRole(role: UserRole) {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading && (!user || user.role !== role)) {
      router.push("/login");
    }
  }, [user, loading, role, router]);
  return { user, loading };
}
