import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { LoadingState } from "@/components/feedback/states";
import { AuthShell } from "@/components/layout/auth-shell";
import { ResetPasswordForm } from "@/features/authentication/components/email-forms";

export const metadata: Metadata = { title: "Choose a new password" };

export default function Page() {
  return (
    <AuthShell
      title="Choose a new password"
      subtitle={
        <>
          Links expire after 30 minutes.{" "}
          <Link className="text-primary font-medium hover:underline" href="/forgot-password">
            Request a new one
          </Link>
        </>
      }
    >
      <Suspense fallback={<LoadingState />}>
        <ResetPasswordForm />
      </Suspense>
    </AuthShell>
  );
}
