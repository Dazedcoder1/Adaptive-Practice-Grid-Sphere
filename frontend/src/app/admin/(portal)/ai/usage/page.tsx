import type { Metadata } from "next";
import { AiUsagePage } from "@/features/admin/ai/usage";

export const metadata: Metadata = { title: "AI usage" };

export default function Page() {
  return <AiUsagePage />;
}
