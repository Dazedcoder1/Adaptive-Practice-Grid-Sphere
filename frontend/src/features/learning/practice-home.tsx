"use client";

import { useQuery } from "@tanstack/react-query";
import { ClipboardCheck, Play, Target } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { formatRelative } from "@/lib/utils";
import { learning } from "./api";
import { useStartSession } from "./use-start-session";

export function PracticeHome() {
  const tree = useQuery({ queryKey: ["my-curriculum"], queryFn: learning.myCurriculum });
  const open = useQuery({ queryKey: ["sessions", "open"], queryFn: () => learning.sessions("open") });
  const done = useQuery({ queryKey: ["sessions", "completed"], queryFn: () => learning.sessions("completed") });
  const start = useStartSession();
  const [chapterId, setChapterId] = useState<string>("");
  const [count, setCount] = useState("10");

  if (tree.isLoading) return <LoadingState />;
  if (tree.isError || !tree.data) return <ErrorState onRetry={() => void tree.refetch()} />;

  const chapters = tree.data.subjects.flatMap((s) =>
    s.chapters.map((c) => ({
      ...c,
      subject: s.name,
      practisable: c.practisable ?? c.topics.some((t) => t.concepts.some((x) => x.question_count > 0)),
    })),
  );
  const usable = chapters.filter((c) => c.practisable);
  const selected = chapterId || String(usable[0]?.id ?? "");

  return (
    <>
      <PageHeader
        title="Practice"
        description="Questions are chosen for you from what you already know, one at a time."
      />

      {(open.data?.length ?? 0) > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Continue where you left off</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y">
              {open.data!.map((s) => (
                <li key={s.id} className="flex items-center justify-between gap-3 py-3">
                  <div>
                    <p className="text-sm font-medium">{s.title}</p>
                    <p className="text-muted-foreground text-xs">
                      {s.answered_count} of {s.target_count} answered · {formatRelative(s.last_activity_at)}
                    </p>
                  </div>
                  <Button asChild size="sm" variant="gradient">
                    <Link href={`/practice/${s.id}`}>
                      <Play /> {s.status === "paused" ? "Resume" : "Continue"}
                    </Link>
                  </Button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Start a session</CardTitle>
          <CardDescription>
            Adaptive practice targets your weakest concepts and adjusts difficulty as you go. A diagnostic asks one
            question per concept to estimate where you are.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {usable.length === 0 ? (
            <EmptyState
              title="No practice questions yet"
              description="Questions for your syllabus haven't been published yet."
            />
          ) : (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <label className="flex flex-1 flex-col gap-1.5 text-sm font-medium">
                Chapter
                <Select value={selected} onChange={(e) => setChapterId(e.target.value)}>
                  {chapters.map((c) => (
                    <option key={c.id} value={c.id} disabled={!c.practisable}>
                      {c.subject} · {c.name}
                      {!c.practisable ? " (no questions yet)" : ""}
                    </option>
                  ))}
                </Select>
              </label>
              <label className="flex flex-col gap-1.5 text-sm font-medium">
                Questions
                <Select value={count} onChange={(e) => setCount(e.target.value)}>
                  {[5, 10, 15, 20].map((n) => (
                    <option key={n}>{n}</option>
                  ))}
                </Select>
              </label>
              <Button
                variant="outline"
                loading={start.isPending && start.variables?.mode === "diagnostic"}
                onClick={() => start.mutate({ mode: "diagnostic", chapter_id: Number(selected) })}
              >
                <ClipboardCheck /> Diagnostic
              </Button>
              <Button
                variant="gradient"
                loading={start.isPending && start.variables?.mode === "adaptive"}
                onClick={() => start.mutate({ mode: "adaptive", chapter_id: Number(selected), count: Number(count) })}
              >
                <Target /> Adaptive practice
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Past sessions</CardTitle>
        </CardHeader>
        <CardContent>
          {done.isLoading ? (
            <LoadingState />
          ) : !done.data?.length ? (
            <p className="text-muted-foreground text-sm">Completed sessions and their reports appear here.</p>
          ) : (
            <ul className="divide-y">
              {done.data.map((s) => (
                <li key={s.id}>
                  <Link
                    href={`/practice/${s.id}/report`}
                    className="hover:bg-muted/50 -mx-2 flex items-center justify-between gap-3 rounded-lg px-2 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium">{s.title}</p>
                      <p className="text-muted-foreground text-xs">{formatRelative(s.completed_at)}</p>
                    </div>
                    <Badge
                      variant={s.answered_count && s.correct_count / s.answered_count >= 0.7 ? "success" : "muted"}
                    >
                      {s.correct_count}/{s.answered_count} correct
                    </Badge>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </>
  );
}
