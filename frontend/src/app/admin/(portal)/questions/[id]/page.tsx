"use client";

import { useParams } from "next/navigation";
import { QuestionEditor } from "@/features/admin/question-editor";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  return <QuestionEditor id={id} />;
}
