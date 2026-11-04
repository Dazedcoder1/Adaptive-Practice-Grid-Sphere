"use client";

import { useParams } from "next/navigation";
import { AiDocumentDetail } from "@/features/admin/ai/document-detail";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  return <AiDocumentDetail id={id} />;
}
