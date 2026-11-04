"use client";

import { useParams } from "next/navigation";
import { PracticePlayer } from "@/features/learning/practice-player";

export default function Page() {
  const params = useParams<{ sessionId: string }>();
  return <PracticePlayer sessionId={params.sessionId} />;
}
