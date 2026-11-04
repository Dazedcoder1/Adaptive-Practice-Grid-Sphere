import type { Metadata } from "next";

import { Suspense } from "react";
import { LoadingState } from "@/components/feedback/states";
import { AuthShell } from "@/components/layout/auth-shell";
import { RedirectIfAuthenticated } from "@/features/authentication/guards";
import { LoginForm } from "@/features/authentication/components/login-form";

export const metadata: Metadata = { title: "Super Admin sign in" };

export default function Page() {
  return (
    <AuthShell
      title="Super Admin sign in"
      subtitle={"Restricted to platform administrators. All activity is audited."}
      aside="admin"
    >
      <Suspense fallback={<LoadingState />}>
        <RedirectIfAuthenticated portal="admin">
          <LoginForm portal="admin" />
        </RedirectIfAuthenticated>
      </Suspense>
    </AuthShell>
  );
}
