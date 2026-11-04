import type { Metadata } from "next";
import { AiOverviewPage } from "@/features/admin/ai/overview";

export const metadata: Metadata = { title: "AI & RAG" };

export default function Page() {
  return <AiOverviewPage />;
}
