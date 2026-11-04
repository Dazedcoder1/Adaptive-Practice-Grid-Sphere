"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime, formatRelative } from "@/lib/utils";
import { adminApi } from "./api";
import { UserStatusBadge } from "./status-badge";

export function UsersList() {
  const router = useRouter();
  const params = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [debounced, setDebounced] = useState(q);
  const [status, setStatus] = useState(params.get("status") ?? "");
  const [role, setRole] = useState(params.get("role") ?? "student");
  const [deletion, setDeletion] = useState(params.get("deletion") === "1");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  const users = useQuery({
    queryKey: ["admin", "users", debounced, status, role, deletion, page],
    queryFn: () =>
      adminApi.users({ q: debounced, status, role, deletion_requested: deletion || undefined, page, page_size: 20 }),
    placeholderData: keepPreviousData,
  });

  return (
    <>
      <PageHeader
        title="User management"
        description="Search, review and manage accounts. Sensitive details are only shown where needed."
      />
      <Card>
        <div className="flex flex-col gap-3 border-b p-4 md:flex-row md:items-center">
          <div className="relative flex-1">
            <Search className="text-muted-foreground absolute top-1/2 left-3 size-4 -translate-y-1/2" aria-hidden />
            <Input
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
              placeholder="Search by name or email"
              className="pl-9"
              aria-label="Search users"
            />
          </div>
          <Select
            value={role}
            onChange={(e) => {
              setRole(e.target.value);
              setPage(1);
            }}
            aria-label="Role"
          >
            <option value="">All roles</option>
            <option value="student">Students</option>
            <option value="super_admin">Super Admins</option>
          </Select>
          <Select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            aria-label="Status"
          >
            <option value="">Any status</option>
            <option value="active">Active</option>
            <option value="pending_verification">Unverified</option>
            <option value="pending_consent">Awaiting guardian</option>
            <option value="suspended">Suspended</option>
          </Select>
          <label className="flex items-center gap-2 text-sm whitespace-nowrap">
            <input
              type="checkbox"
              checked={deletion}
              onChange={(e) => {
                setDeletion(e.target.checked);
                setPage(1);
              }}
              className="accent-primary size-4"
            />
            Deletion requested
          </label>
        </div>
        {users.isLoading ? (
          <LoadingState />
        ) : users.isError ? (
          <ErrorState onRetry={() => void users.refetch()} />
        ) : users.data?.items.length === 0 ? (
          <EmptyState title="No users match" description="Try a different search or filter." />
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>User</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="hidden md:table-cell">Joined</TableHead>
                  <TableHead className="hidden md:table-cell">Last sign-in</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.data?.items.map((u) => (
                  <TableRow key={u.id} className="cursor-pointer" onClick={() => router.push(`/admin/users/${u.id}`)}>
                    <TableCell>
                      <p className="font-medium">{u.display_name ?? "—"}</p>
                      <p className="text-muted-foreground text-xs">{u.email}</p>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        <UserStatusBadge status={u.status} />
                        {u.roles.includes("super_admin") && <Badge>Admin</Badge>}
                        {u.is_minor && <Badge variant="outline">Under 18</Badge>}
                        {u.deletion_requested_at && <Badge variant="warning">Deletion requested</Badge>}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground hidden md:table-cell">
                      {formatDateTime(u.created_at)}
                    </TableCell>
                    <TableCell className="text-muted-foreground hidden md:table-cell">
                      {formatRelative(u.last_login_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={page} pageSize={20} total={users.data?.total ?? 0} onPage={setPage} />
          </>
        )}
      </Card>
    </>
  );
}
