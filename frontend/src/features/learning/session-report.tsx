"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, CircleDashed, Clock, RotateCcw, Target, XCircle } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { StatCard } from "@/components/dashboard/stat-card";
import { ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { Markdown } from "@/components/questions/markdown";
import { formatDuration, LevelBadge } from "@/components/questions/mastery-bar";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { learning } from "./api";
import { useStartSession } from "./use-start-session";

const RESULT = {
  correct: { icon: CheckCircle2, cls: "text-success", label: "Correct" },
  partial: { icon: CircleDashed, cls: "text-warning", label: "Partly correct" },
  incorrect: { icon: XCircle, cls: "text-destructive", label: "Incorrect" },
  ungraded: { icon: CircleDashed, cls: "text-accent", label: "Not auto-marked" },
} as const;

export function SessionReport({ sessionId }: { sessionId: string }) {
  const exhausted = useSearchParams().get("exhausted") === "1";
  const report = useQuery({ queryKey: ["report", sessionId], queryFn: () => learning.report(sessionId) });
  const start = useStartSession();

  if (report.isLoading) return <LoadingState />;
  if (report.isError || !report.data)
    return (
      <ErrorState
        message={report.error instanceof ApiError ? report.error.message : undefined}
        onRetry={() => void report.refetch()}
      />
    );
  const r = report.data;
  const weakIds = r.weak_concepts.map((w) => w.concept_id);

  return (
    <>
      <PageHeader
        title="Session report"
        description={r.session.title}
        actions={
          <Button asChild variant="outline">
            <Link href="/practice">Back to practice</Link>
          </Button>
        }
      />
      {exhausted && (
        <Alert variant="info" className="mb-4">
          <CircleDashed />
          You&apos;ve answered every available question in this scope, so the session ended early.
        </Alert>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Accuracy"
          value={r.accuracy == null ? "—" : `${Math.round(r.accuracy * 100)}%`}
          icon={Target}
          hint={`${r.session.correct_count} of ${r.session.answered_count} correct`}
        />
        <StatCard label="Time spent" value={formatDuration(r.session.active_seconds)} icon={Clock} />
        <StatCard
          label="Added to revision"
          value={r.weak_concepts.length}
          icon={RotateCcw}
          tone={r.weak_concepts.length ? "warning" : "default"}
          hint={r.weak_concepts.length ? "Weak concepts are scheduled for review" : "No weak concepts this time"}
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_22rem]">
        <Card>
          <CardHeader>
            <CardTitle>Questions</CardTitle>
          </CardHeader>
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>#</TableHead>
                <TableHead>Question</TableHead>
                <TableHead className="hidden sm:table-cell">Concept</TableHead>
                <TableHead className="text-right">Result</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {r.questions.map((q) => {
                const res = RESULT[q.evaluation];
                return (
                  <TableRow key={q.position}>
                    <TableCell className="text-muted-foreground">{q.position}</TableCell>
                    <TableCell className="max-w-xs">
                      <Markdown className="line-clamp-2">{q.stem}</Markdown>
                      <p className="text-muted-foreground mt-0.5 text-xs">
                        Difficulty {q.difficulty} · {formatDuration(q.time_taken_seconds)}
                        {q.hints_used > 0 && ` · ${q.hints_used} hint${q.hints_used > 1 ? "s" : ""}`}
                      </p>
                    </TableCell>
                    <TableCell className="text-muted-foreground hidden text-xs sm:table-cell">{q.concept}</TableCell>
                    <TableCell className="text-right">
                      <span className={cn("inline-flex items-center gap-1 text-xs font-medium", res.cls)}>
                        <res.icon className="size-4" aria-hidden /> {res.label}
                      </span>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Mastery changes</CardTitle>
              <CardDescription>Estimates from the {r.model_version} knowledge model.</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3 text-sm">
                {r.concepts.map((c) => (
                  <li key={c.concept_id}>
                    <div className="flex items-center justify-between gap-2">
                      <Link href={`/learn/${c.concept_id}`} className="font-medium hover:underline">
                        {c.name}
                      </Link>
                      <LevelBadge level={c.level} />
                    </div>
                    <p className="text-muted-foreground mt-0.5 text-xs tabular-nums">
                      {Math.round(c.before * 100)}% →{" "}
                      <strong className="text-foreground">{Math.round(c.after * 100)}%</strong> · {c.answered} answered
                    </p>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
          {weakIds.length > 0 && (
            <Card className="border-warning/30">
              <CardHeader>
                <CardTitle>Focus next</CardTitle>
                <CardDescription>These are now in your revision plan.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <ul className="text-sm">
                  {r.weak_concepts.map((w) => (
                    <li key={w.concept_id} className="py-0.5">
                      {w.name}
                    </li>
                  ))}
                </ul>
                <Button
                  variant="gradient"
                  className="w-full"
                  loading={start.isPending}
                  onClick={() => start.mutate({ mode: "adaptive", concept_ids: weakIds })}
                >
                  Practise weak concepts <ArrowRight />
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
