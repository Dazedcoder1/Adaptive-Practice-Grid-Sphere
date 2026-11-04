import type { Metadata } from "next";
import { PlannedFeature } from "@/components/feedback/planned-feature";
import { adminPlanned } from "@/features/planned/catalog";

const entry = adminPlanned["exams"];
export const metadata: Metadata = { title: entry.title };

export default function Page() {
  return <PlannedFeature {...entry} />;
}
