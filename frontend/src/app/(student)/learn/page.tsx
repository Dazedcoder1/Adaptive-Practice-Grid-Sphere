import type { Metadata } from "next";
import { PlannedFeature } from "@/components/feedback/planned-feature";
import { studentPlanned } from "@/features/planned/catalog";

const entry = studentPlanned["learn"];
export const metadata: Metadata = { title: entry.title };

export default function Page() {
  return <PlannedFeature {...entry} />;
}
