import { Suspense } from "react";
import { LoadingState } from "@/components/feedback/states";
import { QuestionList } from "@/features/admin/question-list";

export default function Page() {
  return (
    <Suspense fallback={<LoadingState />}>
      <QuestionList />
    </Suspense>
  );
}
