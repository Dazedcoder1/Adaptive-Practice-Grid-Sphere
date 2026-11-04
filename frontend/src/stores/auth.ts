import { create } from "zustand";
import type { AuthUser } from "@/types/api";

/**
 * Who is signed in. The access token lives only in memory (never localStorage), so an
 * XSS bug can't lift a long-lived credential; the refresh token is an httpOnly cookie
 * the browser sends to /api/v1/auth only.
 */
type AuthStatus = "loading" | "authenticated" | "anonymous";

type AuthState = {
  status: AuthStatus;
  accessToken: string | null;
  user: AuthUser | null;
  setSession: (token: string, user: AuthUser) => void;
  setUser: (user: AuthUser) => void;
  clear: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  status: "loading",
  accessToken: null,
  user: null,
  setSession: (accessToken, user) => set({ accessToken, user, status: "authenticated" }),
  setUser: (user) => set({ user }),
  clear: () => set({ accessToken: null, user: null, status: "anonymous" }),
}));

export const isAdmin = (u: AuthUser | null) => !!u?.roles.includes("super_admin");
export const isStudent = (u: AuthUser | null) => !!u?.roles.includes("student");
