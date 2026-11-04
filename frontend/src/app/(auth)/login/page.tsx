import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { LoadingState } from "@/components/feedback/states";
import { AuthShell } from "@/components/layout/auth-shell";
import { RedirectIfAuthenticated } from "@/features/authentication/guards";
import { LoginForm } from "@/features/authentication/components/login-form";

export const metadata: Metadata = { title: "Sign in" };

export default function Page() {
  return (
    <AuthShell
      title="Sign in"
      subtitle={
        <>
          New here?{" "}
          <Link className="text-primary font-medium hover:underline" href="/register">
            Create an account
          </Link>
        </>
      }
    >
      <Suspense fallback={<LoadingState />}>
        <RedirectIfAuthenticated portal="student">
          <LoginForm portal="student" />
        </RedirectIfAuthenticated>
      </Suspense>
    </AuthShell>
  );
}
