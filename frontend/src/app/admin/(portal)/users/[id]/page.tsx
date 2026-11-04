"use client";

import { useParams } from "next/navigation";
import { UserDetail } from "@/features/admin/user-detail";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  return <UserDetail id={id} />;
}
