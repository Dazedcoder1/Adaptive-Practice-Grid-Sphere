"use client";

import { useParams } from "next/navigation";
import { Suspense } from "react";
import { LoadingState } from "@/components/feedback/states";
import { SessionReport } from "@/features/learning/session-report";

export default function Page() {
  const { sessionId } = useParams<{ sessionId: string }>();
  return (
    <Suspense fallback={<LoadingState />}>
      <SessionReport sessionId={sessionId} />
    </Suspense>
  );
}
