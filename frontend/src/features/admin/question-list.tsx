"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { CheckCircle2, FileQuestion, Inbox, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { StatCard } from "@/components/dashboard/stat-card";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { Markdown } from "@/components/questions/markdown";
import { TYPE_LABEL } from "@/components/questions/question-view";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatRelative } from "@/lib/utils";
import { contentApi, type QStatus } from "./content-api";

export const STATUS_BADGE: Record<
  QStatus,
  { label: string; variant: "success" | "warning" | "destructive" | "muted" | "blue" }
> = {
  draft: { label: "Draft", variant: "muted" },
  in_review: { label: "In review", variant: "warning" },
  rejected: { label: "Changes requested", variant: "destructive" },
  published: { label: "Published", variant: "success" },
  archived: { label: "Archived", variant: "muted" },
};

export function QuestionList() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [page, setPage] = useState(1);
  const conceptId = useSearchParams().get("concept_id") ?? "";
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  const stats = useQuery({ queryKey: ["admin", "qstats"], queryFn: contentApi.stats });
  const list = useQuery({
    queryKey: ["admin", "questions", debounced, status, type, difficulty, conceptId, page],
    queryFn: () => contentApi.questions({ q: debounced, status, type, difficulty, concept_id: conceptId, page }),
    placeholderData: keepPreviousData,
  });
  const reset = (fn: (v: string) => void) => (v: string) => {
    fn(v);
    setPage(1);
  };

  return (
    <>
      <PageHeader
        title="Question bank"
        description="Versioned questions with a review step before anything reaches students. Answer keys never leave the server."
        actions={
          <Button asChild variant="gradient">
            <Link href="/admin/questions/new">
              <Plus /> New question
            </Link>
          </Button>
        }
      />
      {stats.data && (
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <StatCard label="Questions" value={stats.data.questions_total} icon={FileQuestion} />
          <StatCard label="Published" value={stats.data.questions_published} icon={CheckCircle2} />
          <StatCard
            label="Approval backlog"
            value={stats.data.approval_backlog}
            icon={Inbox}
            tone={stats.data.approval_backlog ? "warning" : "default"}
          />
        </div>
      )}
      <Card>
        {conceptId && (
          <div className="flex items-center gap-2 border-b px-4 py-2 text-sm">
            <Badge variant="blue">Filtered to one concept</Badge>
            <Link href="/admin/questions" className="text-primary text-xs hover:underline">
              Clear
            </Link>
          </div>
        )}
        <div className="flex flex-col gap-3 border-b p-4 md:flex-row">
          <div className="relative flex-1">
            <Search className="text-muted-foreground absolute top-1/2 left-3 size-4 -translate-y-1/2" aria-hidden />
            <Input
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
              placeholder="Search question text"
              className="pl-9"
              aria-label="Search questions"
            />
          </div>
          <Select value={status} onChange={(e) => reset(setStatus)(e.target.value)} aria-label="Status">
            <option value="">Any status</option>
            {Object.entries(STATUS_BADGE).map(([k, v]) => (
              <option key={k} value={k}>
                {v.label}
              </option>
            ))}
          </Select>
          <Select value={type} onChange={(e) => reset(setType)(e.target.value)} aria-label="Type">
            <option value="">Any type</option>
            {Object.entries(TYPE_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </Select>
          <Select value={difficulty} onChange={(e) => reset(setDifficulty)(e.target.value)} aria-label="Difficulty">
            <option value="">Any difficulty</option>
            {[1, 2, 3, 4, 5].map((d) => (
              <option key={d} value={d}>
                Difficulty {d}
              </option>
            ))}
          </Select>
        </div>
        {list.isLoading ? (
          <LoadingState />
        ) : list.isError ? (
          <ErrorState onRetry={() => void list.refetch()} />
        ) : !list.data?.items.length ? (
          <EmptyState title="No questions match" description="Change the filters, or create a question." />
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Question</TableHead>
                  <TableHead className="hidden md:table-cell">Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="hidden lg:table-cell">Attempts</TableHead>
                  <TableHead className="hidden lg:table-cell">Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.data.items.map((row) => (
                  <TableRow
                    key={row.id}
                    className="cursor-pointer"
                    onClick={() => router.push(`/admin/questions/${row.id}`)}
                  >
                    <TableCell className="max-w-md">
                      <Markdown className="line-clamp-2">{row.stem}</Markdown>
                      <p className="text-muted-foreground mt-0.5 text-xs">
                        {row.concepts.join(", ")} · difficulty {row.difficulty} · v{row.version}
                        {row.is_sample && " · sample"}
                      </p>
                    </TableCell>
                    <TableCell className="text-muted-foreground hidden text-xs md:table-cell">
                      {TYPE_LABEL[row.type]}
                    </TableCell>
                    <TableCell>
                      <Badge variant={STATUS_BADGE[row.status].variant}>{STATUS_BADGE[row.status].label}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground hidden lg:table-cell">{row.attempts}</TableCell>
                    <TableCell className="text-muted-foreground hidden text-xs lg:table-cell">
                      {formatRelative(row.updated_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={page} pageSize={20} total={list.data.total} onPage={setPage} />
          </>
        )}
      </Card>
    </>
  );
}
