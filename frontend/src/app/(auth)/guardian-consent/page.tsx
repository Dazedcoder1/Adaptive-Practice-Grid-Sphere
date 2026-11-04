import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { LoadingState } from "@/components/feedback/states";
import { AuthShell } from "@/components/layout/auth-shell";
import { TokenAction } from "@/features/authentication/components/email-forms";

export const metadata: Metadata = { title: "Parent or guardian consent" };

export default function Page() {
  return (
    <AuthShell
      title="Parent or guardian consent"
      subtitle={
        <>
          A student under 18 listed you as their parent or guardian. Opening this link records your consent for them to
          use AdaptiveLearn AI.{" "}
          <Link className="text-primary font-medium hover:underline" href="/">
            About AdaptiveLearn AI
          </Link>
        </>
      }
    >
      <Suspense fallback={<LoadingState />}>
        <TokenAction kind="consent" />
      </Suspense>
    </AuthShell>
  );
}
