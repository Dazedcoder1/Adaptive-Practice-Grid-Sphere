import type { Metadata } from "next";

import { Suspense } from "react";
import { LoadingState } from "@/components/feedback/states";
import { AuthShell } from "@/components/layout/auth-shell";
import { TokenAction } from "@/features/authentication/components/email-forms";

export const metadata: Metadata = { title: "Verify your email" };

export default function Page() {
  return (
    <AuthShell title="Verify your email" subtitle={"Confirming that this email address belongs to you."}>
      <Suspense fallback={<LoadingState />}>
        <TokenAction kind="verify" />
      </Suspense>
    </AuthShell>
  );
}
