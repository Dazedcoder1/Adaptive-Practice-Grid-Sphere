import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { LoadingState } from "@/components/feedback/states";
import { AuthShell } from "@/components/layout/auth-shell";
import { RedirectIfAuthenticated } from "@/features/authentication/guards";
import { RegisterForm } from "@/features/authentication/components/register-form";

export const metadata: Metadata = { title: "Create your account" };

export default function Page() {
  return (
    <AuthShell
      title="Create your account"
      subtitle={
        <>
          Already have one?{" "}
          <Link className="text-primary font-medium hover:underline" href="/login">
            Sign in
          </Link>
        </>
      }
    >
      <Suspense fallback={<LoadingState />}>
        <RedirectIfAuthenticated portal="student">
          <RegisterForm />
        </RedirectIfAuthenticated>
      </Suspense>
    </AuthShell>
  );
}
