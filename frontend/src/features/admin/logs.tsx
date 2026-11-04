"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime } from "@/lib/utils";
import { adminApi } from "./api";

function useDebounced<T>(value: T, ms = 300) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function AuditLogs() {
  const [action, setAction] = useState("");
  const debounced = useDebounced(action);
  const [page, setPage] = useState(1);
  const logs = useQuery({
    queryKey: ["admin", "audit", debounced, page],
    queryFn: () => adminApi.auditLogs({ action: debounced, page }),
    placeholderData: keepPreviousData,
  });

  return (
    <>
      <PageHeader
        title="Audit logs"
        description="Append-only record of administrative and sensitive account actions."
      />
      <Card>
        <div className="border-b p-4">
          <div className="relative max-w-sm">
            <Search className="text-muted-foreground absolute top-1/2 left-3 size-4 -translate-y-1/2" aria-hidden />
            <Input
              value={action}
              onChange={(e) => {
                setAction(e.target.value);
                setPage(1);
              }}
              placeholder="Filter by action, e.g. suspended"
              className="pl-9"
              aria-label="Filter by action"
            />
          </div>
        </div>
        {logs.isLoading ? (
          <LoadingState />
        ) : logs.isError ? (
          <ErrorState onRetry={() => void logs.refetch()} />
        ) : logs.data?.items.length === 0 ? (
          <EmptyState title="No entries" />
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>When</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead className="hidden md:table-cell">Target</TableHead>
                  <TableHead className="hidden lg:table-cell">Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.data?.items.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="text-muted-foreground whitespace-nowrap">
                      {formatDateTime(a.created_at)}
                    </TableCell>
                    <TableCell>
                      <code className="bg-muted rounded px-1.5 py-0.5 text-xs">{a.action}</code>
                    </TableCell>
                    <TableCell>{a.actor_email ?? <span className="text-muted-foreground">system</span>}</TableCell>
                    <TableCell className="hidden md:table-cell">
                      {a.target_type === "user" && a.target_id ? (
                        <Link className="text-primary hover:underline" href={`/admin/users/${a.target_id}`}>
                          user
                        </Link>
                      ) : (
                        <span className="text-muted-foreground">{a.target_type ?? "—"}</span>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground hidden max-w-xs truncate text-xs lg:table-cell">
                      {Object.keys(a.details).length ? JSON.stringify(a.details) : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={page} pageSize={50} total={logs.data?.total ?? 0} onPage={setPage} />
          </>
        )}
      </Card>
    </>
  );
}

export function SecurityPage() {
  const [result, setResult] = useState<"" | "false" | "true">("false");
  const [email, setEmail] = useState("");
  const debounced = useDebounced(email);
  const [page, setPage] = useState(1);
  const events = useQuery({
    queryKey: ["admin", "logins", result, debounced, page],
    queryFn: () =>
      adminApi.loginEvents({ success: result === "" ? undefined : result === "true", email: debounced, page }),
    placeholderData: keepPreviousData,
  });

  return (
    <>
      <PageHeader
        title="Security"
        description="Sign-in activity across both portals. Repeated failures are rate-limited automatically."
      />
      <Card>
        <CardHeader>
          <CardTitle>Login activity</CardTitle>
          <CardDescription>Failed attempts are shown by default.</CardDescription>
        </CardHeader>
        <div className="flex flex-col gap-3 border-y p-4 sm:flex-row">
          <Input
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setPage(1);
            }}
            placeholder="Filter by email"
            className="sm:max-w-xs"
            aria-label="Filter by email"
          />
          <Select
            value={result}
            onChange={(e) => {
              setResult(e.target.value as typeof result);
              setPage(1);
            }}
            aria-label="Result"
          >
            <option value="false">Failed only</option>
            <option value="true">Successful only</option>
            <option value="">All</option>
          </Select>
        </div>
        <CardContent className="p-0">
          {events.isLoading ? (
            <LoadingState />
          ) : events.isError ? (
            <ErrorState onRetry={() => void events.refetch()} />
          ) : events.data?.items.length === 0 ? (
            <EmptyState title="No sign-in events" />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>When</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Portal</TableHead>
                    <TableHead>Result</TableHead>
                    <TableHead className="hidden md:table-cell">IP</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.data?.items.map((e) => (
                    <TableRow key={e.id}>
                      <TableCell className="text-muted-foreground whitespace-nowrap">
                        {formatDateTime(e.created_at)}
                      </TableCell>
                      <TableCell>{e.email}</TableCell>
                      <TableCell className="capitalize">{e.portal}</TableCell>
                      <TableCell>
                        <Badge variant={e.success ? "success" : "destructive"}>
                          {e.success ? "Success" : e.reason?.replace(/_/g, " ")}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground hidden md:table-cell">
                        {e.ip_address ?? "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Pagination page={page} pageSize={50} total={events.data?.total ?? 0} onPage={setPage} />
            </>
          )}
        </CardContent>
      </Card>
    </>
  );
}

export function SettingsPage() {
  const health = useQuery({ queryKey: ["health"], queryFn: adminApi.health, refetchInterval: 30_000 });
  const roles = useQuery({ queryKey: ["admin", "roles"], queryFn: adminApi.roles });
  const dead = useQuery({ queryKey: ["admin", "dead"], queryFn: () => adminApi.deadLetters(1) });

  return (
    <>
      <PageHeader title="System settings" description="Infrastructure health, roles and background job failures." />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Dependencies</CardTitle>
            <CardDescription>Database, cache/queue and object storage.</CardDescription>
          </CardHeader>
          <CardContent>
            {health.isLoading ? (
              <LoadingState />
            ) : !health.data ? (
              <p className="text-destructive text-sm">Health endpoint unreachable.</p>
            ) : (
              <ul className="divide-y text-sm">
                {Object.entries(health.data).map(([k, v]) => (
                  <li key={k} className="flex items-center justify-between gap-3 py-2.5">
                    <span className="capitalize">{k}</span>
                    <span
                      className={
                        v === "ok"
                          ? "text-success"
                          : v === "not configured"
                            ? "text-warning"
                            : "text-destructive max-w-xs truncate"
                      }
                      title={v}
                    >
                      {v}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Roles & permissions</CardTitle>
            <CardDescription>Seeded by migrations. Only two portals exist: Student and Super Admin.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {roles.data?.map((r) => (
              <div key={r.name}>
                <p className="text-sm font-medium">
                  {r.name} <span className="text-muted-foreground font-normal">— {r.description}</span>
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {r.permissions.length ? (
                    r.permissions.map((p) => (
                      <Badge key={p} variant="outline">
                        {p}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-muted-foreground text-xs">Own data only</span>
                  )}
                </div>
              </div>
            )) ?? <LoadingState />}
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Failed background jobs</CardTitle>
            <CardDescription>Event consumers that exhausted their retries (dead letters).</CardDescription>
          </CardHeader>
          <CardContent>
            {dead.isLoading ? (
              <LoadingState />
            ) : !dead.data?.items.length ? (
              <EmptyState
                title="No failed jobs"
                description="Every background job has completed or is still retrying."
              />
            ) : (
              <ul className="divide-y text-sm">
                {dead.data.items.map((d) => (
                  <li key={d.id} className="py-2.5">
                    <p className="font-mono text-xs">{d.task_name}</p>
                    <p className="text-destructive text-xs">{d.error}</p>
                    <p className="text-muted-foreground text-xs">{formatDateTime(d.created_at)}</p>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-muted-foreground mt-4 text-xs">
              Backup status and restore procedures: see docs/operations.md (Neon manages point-in-time backups).
            </p>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
