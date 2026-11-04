import type { Metadata } from "next";
import { AiDocumentsPage } from "@/features/admin/ai/documents";

export const metadata: Metadata = { title: "AI documents" };

export default function Page() {
  return <AiDocumentsPage />;
}
