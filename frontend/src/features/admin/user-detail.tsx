"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Ban, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { formatDateTime } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import { adminApi } from "./api";
import { UserStatusBadge } from "./status-badge";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 py-2.5 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  );
}

export function UserDetail({ id }: { id: string }) {
  const qc = useQueryClient();
  const me = useAuthStore((s) => s.user);
  const [reason, setReason] = useState("");
  const user = useQuery({ queryKey: ["admin", "user", id], queryFn: () => adminApi.user(id) });
  const change = useMutation({
    mutationFn: (action: "suspend" | "activate") =>
      action === "suspend" ? adminApi.suspend(id, reason) : adminApi.activate(id, reason || undefined),
    onSuccess: (u) => {
      qc.setQueryData(["admin", "user", id], u);
      void qc.invalidateQueries({ queryKey: ["admin", "users"] });
      void qc.invalidateQueries({ queryKey: ["admin", "stats"] });
      setReason("");
      toast.success(u.status === "suspended" ? "Account suspended and signed out everywhere" : "Account activated");
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Something went wrong."),
  });

  if (user.isLoading) return <LoadingState />;
  if (user.isError || !user.data)
    return (
      <ErrorState
        message={user.error instanceof ApiError ? user.error.message : undefined}
        onRetry={() => void user.refetch()}
      />
    );
  const u = user.data;
  const self = me?.id === u.id;
  const suspend = u.status !== "suspended";

  return (
    <>
      <Link
        href="/admin/users"
        className="text-muted-foreground hover:text-foreground mb-4 inline-flex items-center gap-1.5 text-sm"
      >
        <ArrowLeft className="size-4" /> All users
      </Link>
      <PageHeader
        title={u.display_name ?? u.email}
        description={u.email}
        actions={
          !self && (
            <Dialog>
              <DialogTrigger asChild>
                <Button variant={suspend ? "destructive" : "default"}>
                  {suspend ? (
                    <>
                      <Ban /> Suspend
                    </>
                  ) : (
                    <>
                      <CheckCircle2 /> Activate
                    </>
                  )}
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{suspend ? "Suspend this account?" : "Activate this account?"}</DialogTitle>
                  <DialogDescription>
                    {suspend
                      ? "They'll be signed out on every device immediately and can't sign in until reactivated."
                      : u.status === "pending_verification" || u.status === "pending_consent"
                        ? "This bypasses email verification or guardian consent. Only do this if you've confirmed it another way."
                        : "They'll be able to sign in again."}
                  </DialogDescription>
                </DialogHeader>
                <FormField id="reason" label="Reason" hint="Recorded in the audit log.">
                  <Input value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} />
                </FormField>
                <DialogFooter>
                  <DialogClose asChild>
                    <Button variant="outline">Cancel</Button>
                  </DialogClose>
                  <DialogClose asChild>
                    <Button
                      variant={suspend ? "destructive" : "default"}
                      disabled={suspend && !reason.trim()}
                      onClick={() => change.mutate(suspend ? "suspend" : "activate")}
                    >
                      {suspend ? "Suspend account" : "Activate account"}
                    </Button>
                  </DialogClose>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )
        }
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Account</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="divide-y">
              <Row label="Status">
                <UserStatusBadge status={u.status} />
              </Row>
              {u.suspended_reason && <Row label="Suspension reason">{u.suspended_reason}</Row>}
              <Row label="Roles">{u.roles.join(", ")}</Row>
              <Row label="Email verified">{formatDateTime(u.email_verified_at)}</Row>
              <Row label="Joined">{formatDateTime(u.created_at)}</Row>
              <Row label="Last sign-in">{formatDateTime(u.last_login_at)}</Row>
              <Row label="Active sessions">{u.active_sessions}</Row>
              {u.is_minor !== null && <Row label="Under 18">{u.is_minor ? "Yes" : "No"}</Row>}
              {u.guardian_email_masked && <Row label="Guardian">{u.guardian_email_masked}</Row>}
              {u.timezone && <Row label="Timezone">{u.timezone}</Row>}
              {u.deletion_requested_at && (
                <Row label="Deletion requested">
                  <Badge variant="warning">{formatDateTime(u.deletion_requested_at)}</Badge>
                </Row>
              )}
            </dl>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recent sign-in activity</CardTitle>
          </CardHeader>
          <CardContent>
            {u.recent_logins.length === 0 ? (
              <p className="text-muted-foreground text-sm">No sign-in attempts yet.</p>
            ) : (
              <ul className="divide-y text-sm">
                {u.recent_logins.map((e) => (
                  <li key={e.id} className="flex items-center justify-between gap-3 py-2.5">
                    <span>
                      {formatDateTime(e.created_at)}
                      <span className="text-muted-foreground ml-2 text-xs">{e.ip_address}</span>
                    </span>
                    <Badge variant={e.success ? "success" : "destructive"}>
                      {e.success ? "Success" : e.reason?.replace(/_/g, " ")}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
      <p className="text-muted-foreground mt-6 text-xs">
        Learning progress for this student will appear here once practice ships (Phase 1).
      </p>
    </>
  );
}
