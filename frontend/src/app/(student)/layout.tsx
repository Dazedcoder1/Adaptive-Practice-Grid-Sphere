import { PortalShell } from "@/components/layout/portal-shell";
import { Suspense } from "react";
import { LoadingState } from "@/components/feedback/states";
import { RequirePortal } from "@/features/authentication/guards";

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  // The guard reads the URL at runtime, so it streams in behind a Suspense boundary.
  return (
    <Suspense fallback={<LoadingState className="min-h-screen" />}>
      <RequirePortal portal="student">
        <PortalShell portal="student">{children}</PortalShell>
      </RequirePortal>
    </Suspense>
  );
}
