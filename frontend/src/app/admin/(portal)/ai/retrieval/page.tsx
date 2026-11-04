import type { Metadata } from "next";
import { AiRetrievalPage } from "@/features/admin/ai/retrieval";

export const metadata: Metadata = { title: "Retrieval testing" };

export default function Page() {
  return <AiRetrievalPage />;
}
