import { Badge } from "@/components/ui/badge";
import type { UserStatus } from "@/types/api";

const MAP: Record<UserStatus, { label: string; variant: "success" | "warning" | "destructive" | "muted" | "blue" }> = {
  active: { label: "Active", variant: "success" },
  pending_verification: { label: "Unverified", variant: "muted" },
  pending_consent: { label: "Awaiting guardian", variant: "blue" },
  suspended: { label: "Suspended", variant: "destructive" },
  deleted: { label: "Deleted", variant: "muted" },
};

export function UserStatusBadge({ status }: { status: UserStatus }) {
  const s = MAP[status] ?? { label: status, variant: "muted" as const };
  return <Badge variant={s.variant}>{s.label}</Badge>;
}
