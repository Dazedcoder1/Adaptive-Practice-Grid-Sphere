"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { LoadingState } from "@/components/feedback/states";
import { useAuthStore } from "@/stores/auth";

/** Sends students who haven't set up their learning path to onboarding first. */
export function OnboardingGate({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const pathname = usePathname();
  const router = useRouter();
  const needs = user?.onboarding_completed === false && pathname !== "/onboarding" && pathname !== "/profile";

  useEffect(() => {
    if (needs) router.replace("/onboarding");
  }, [needs, router]);

  if (needs) return <LoadingState label="Setting up your learning path…" />;
  return <>{children}</>;
}
