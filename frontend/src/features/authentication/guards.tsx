"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { LoadingState } from "@/components/feedback/states";
import { isAdmin, isStudent, useAuthStore } from "@/stores/auth";

/**
 * UX-only gate: hides a portal from the wrong audience and redirects to the right login.
 * Real authorisation happens on the API for every request.
 */
export function RequirePortal({ portal, children }: { portal: "student" | "admin"; children: React.ReactNode }) {
  const { status, user } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();
  const allowed = portal === "admin" ? isAdmin(user) : isStudent(user);

  useEffect(() => {
    if (status === "anonymous") {
      const login = portal === "admin" ? "/admin/login" : "/login";
      router.replace(`${login}?next=${encodeURIComponent(pathname)}`);
    } else if (status === "authenticated" && !allowed) {
      router.replace(portal === "admin" ? "/dashboard" : "/admin");
    }
  }, [status, allowed, portal, pathname, router]);

  if (status !== "authenticated" || !allowed) {
    return <LoadingState label="Checking your session…" className="min-h-screen" />;
  }
  return <>{children}</>;
}

/** Sends already-signed-in users away from login/register pages. */
export function RedirectIfAuthenticated({
  portal,
  children,
}: {
  portal: "student" | "admin";
  children: React.ReactNode;
}) {
  const { status, user } = useAuthStore();
  const router = useRouter();
  useEffect(() => {
    if (status !== "authenticated") return;
    if (portal === "admin" && isAdmin(user)) router.replace("/admin");
    if (portal === "student" && isStudent(user)) router.replace("/dashboard");
  }, [status, user, portal, router]);
  return <>{children}</>;
}

/** Only allow same-site relative paths as post-login redirects (no open redirects). */
export function safeNext(next: string | null, fallback: string) {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : fallback;
}
