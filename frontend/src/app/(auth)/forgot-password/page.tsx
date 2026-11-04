import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { LoadingState } from "@/components/feedback/states";
import { AuthShell } from "@/components/layout/auth-shell";
import { ForgotPasswordForm } from "@/features/authentication/components/email-forms";

export const metadata: Metadata = { title: "Reset your password" };

export default function Page() {
  return (
    <AuthShell
      title="Reset your password"
      subtitle={
        <>
          Remembered it?{" "}
          <Link className="text-primary font-medium hover:underline" href="/login">
            Back to sign in
          </Link>
        </>
      }
    >
      <Suspense fallback={<LoadingState />}>
        <ForgotPasswordForm />
      </Suspense>
    </AuthShell>
  );
}
