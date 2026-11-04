import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingState } from "@/components/feedback/states";
import { TutorPage } from "@/features/tutor/tutor-page";

export const metadata: Metadata = { title: "AI Tutor" };

export default function Page() {
  return (
    <Suspense fallback={<LoadingState />}>
      <TutorPage />
    </Suspense>
  );
}
