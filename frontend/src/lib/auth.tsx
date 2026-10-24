import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, getToken, post, setToken } from "./api";
import { tg } from "./telegram";
import type { Meta, User } from "./types";

interface AuthState {
  user: User | null;
  meta: Meta | null;
  loading: boolean;
  loginWithGoogle: (credential: string, linkToken?: string | null) => Promise<User>;
  logout: () => void;
  refresh: () => Promise<void>;
  setUser: (u: User) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [loading, setLoading] = useState(true);
  const qc = useQueryClient();

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      return;
    }
    try {
      setUser(await api<User>("/me"));
    } catch {
      setToken(null);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        setMeta(await api<Meta>("/meta"));
      } catch {
        /* meta bo'lmasa ham ilova ishlayveradi */
      }
      if (tg?.initData) {
        // Telegram ichida — parolsiz kirish
        try {
          const res = await post<{ token: string; user: User }>("/auth/telegram", { init_data: tg.initData });
          setToken(res.token);
          setUser(res.user);
        } catch {
          await refresh();
        }
      } else {
        await refresh();
      }
      setLoading(false);
    })();
  }, [refresh]);

  const loginWithGoogle = useCallback(
    async (credential: string, linkToken?: string | null) => {
      const res = await post<{ token: string; user: User }>("/auth/google", {
        credential,
        link_token: linkToken || null,
      });
      setToken(res.token);
      setUser(res.user);
      qc.invalidateQueries();
      return res.user;
    },
    [qc],
  );

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    qc.clear();
  }, [qc]);

  const value = useMemo(
    () => ({ user, meta, loading, loginWithGoogle, logout, refresh, setUser }),
    [user, meta, loading, loginWithGoogle, logout, refresh],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("AuthProvider yo'q");
  return ctx;
}
