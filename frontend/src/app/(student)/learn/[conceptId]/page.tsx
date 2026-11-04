"use client";

import { useParams } from "next/navigation";
import { ConceptPage } from "@/features/learning/concept-page";

export default function Page() {
  const params = useParams<{ conceptId: string }>();
  return <ConceptPage id={Number(params.conceptId)} />;
}
