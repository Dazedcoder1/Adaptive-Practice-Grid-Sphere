import { Suspense } from "react";
import { LoadingState } from "@/components/feedback/states";
import { UsersList } from "@/features/admin/users-list";

export default function Page() {
  return (
    <Suspense fallback={<LoadingState />}>
      <UsersList />
    </Suspense>
  );
}
