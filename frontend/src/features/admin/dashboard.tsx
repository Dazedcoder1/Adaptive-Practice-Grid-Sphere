"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertOctagon, Inbox, ShieldX, UserCheck, UserPlus, Users } from "lucide-react";
import Link from "next/link";
import { StatCard } from "@/components/dashboard/stat-card";
import { ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDateTime } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { adminApi } from "./api";

const fmt = (n: number) => n.toLocaleString("en-IN");

export function AdminDashboard() {
  const stats = useQuery({ queryKey: ["admin", "stats"], queryFn: adminApi.stats, refetchInterval: 60_000 });
  const health = useQuery({ queryKey: ["health"], queryFn: adminApi.health, refetchInterval: 30_000 });

  if (stats.isLoading) return <LoadingState />;
  if (stats.isError || !stats.data)
    return (
      <ErrorState
        message={stats.error instanceof ApiError ? stats.error.message : undefined}
        onRetry={() => void stats.refetch()}
      />
    );
  const s = stats.data;

  return (
    <>
      <PageHeader
        title="Platform overview"
        description={`Live figures from the database · updated ${formatDateTime(s.generated_at)}`}
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="Registered students"
          value={fmt(s.total_students)}
          icon={Users}
          hint={`${fmt(s.pending_verification)} unverified · ${fmt(s.pending_guardian_consent)} awaiting guardian`}
        />
        <StatCard label="New registrations (7 days)" value={fmt(s.new_registrations_7d)} icon={UserPlus} />
        <StatCard
          label="Active students (7 days)"
          value={fmt(s.active_students_7d)}
          icon={UserCheck}
          hint="Signed in at least once"
        />
        <StatCard
          label="Failed sign-ins (24h)"
          value={fmt(s.failed_logins_24h)}
          icon={ShieldX}
          tone={s.failed_logins_24h > 20 ? "warning" : "default"}
          hint={
            <Link className="text-primary hover:underline" href="/admin/security">
              View login activity
            </Link>
          }
        />
        <StatCard
          label="Failed background jobs"
          value={fmt(s.failed_jobs)}
          icon={AlertOctagon}
          tone={s.failed_jobs > 0 ? "danger" : "default"}
          hint={`${fmt(s.outbox_backlog)} events waiting to publish`}
        />
        <StatCard
          label="Deletion requests"
          value={fmt(s.deletion_requests)}
          icon={Inbox}
          tone={s.deletion_requests > 0 ? "warning" : "default"}
          hint={
            <Link className="text-primary hover:underline" href="/admin/users?deletion=1">
              Review requests
            </Link>
          }
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>System health</CardTitle>
            <CardDescription>Checked every 30 seconds.</CardDescription>
          </CardHeader>
          <CardContent>
            {health.data ? (
              <ul className="divide-y text-sm">
                {Object.entries(health.data).map(([k, v]) => (
                  <li key={k} className="flex items-center justify-between py-2.5">
                    <span className="capitalize">{k === "r2" ? "Object storage (R2)" : k}</span>
                    <Badge
                      variant={v === "ok" ? "success" : v === "not configured" ? "warning" : "destructive"}
                      title={v}
                    >
                      {v === "ok" ? "Healthy" : v === "not configured" ? "Not configured" : "Error"}
                    </Badge>
                  </li>
                ))}
              </ul>
            ) : health.isLoading ? (
              <LoadingState />
            ) : (
              <p className="text-destructive text-sm">Health endpoint unreachable.</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Content & learning metrics</CardTitle>
            <CardDescription>
              Practice sessions, attempts, question bank size, curriculum coverage and approval backlog.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Badge variant="warning">Available once those modules ship in Phase 1</Badge>
            <p className="text-muted-foreground mt-3 text-sm">
              These are not shown as zero, because the underlying data doesn&apos;t exist yet.
            </p>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
