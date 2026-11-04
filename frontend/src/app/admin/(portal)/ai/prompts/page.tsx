import type { Metadata } from "next";
import { AiPromptsPage } from "@/features/admin/ai/prompts";

export const metadata: Metadata = { title: "Tutor prompts" };

export default function Page() {
  return <AiPromptsPage />;
}
