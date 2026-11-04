"use client";

import { useEffect } from "react";
import { refreshSession } from "@/services/api";
import { useAuthStore } from "@/stores/auth";

/**
 * Restores the session on page load (via the refresh cookie) and refreshes the access
 * token a minute before it expires so active users aren't bounced to the login page.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    if (useAuthStore.getState().status === "loading") void refreshSession();
  }, []);

  useEffect(() => {
    if (!token) return;
    let exp = 0;
    try {
      exp = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).exp * 1000;
    } catch {
      return;
    }
    const ms = Math.max(exp - Date.now() - 60_000, 5_000);
    const t = setTimeout(() => void refreshSession(), ms);
    return () => clearTimeout(t);
  }, [token]);

  return <>{children}</>;
}
