"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, CheckCircle2, NotebookPen, RotateCcw, Target, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { Markdown } from "@/components/questions/markdown";
import { LevelBadge, MasteryBar } from "@/components/questions/mastery-bar";
import { QuestionView, TYPE_LABEL } from "@/components/questions/question-view";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { formatDue, formatRelative } from "@/lib/utils";
import { ApiError } from "@/services/api";
import type { MistakeCategory, NotebookEntry, RevisionItem } from "@/types/learning";
import { learning } from "./api";
import { useStartSession } from "./use-start-session";

const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong.");

// ── Revision centre ──────────────────────────────────────────────────────────

function RevisionRow({ item, due }: { item: RevisionItem; due: boolean }) {
  const start = useStartSession();
  return (
    <li className="grid items-center gap-3 py-3 sm:grid-cols-[1fr_9rem_auto]">
      <div className="min-w-0">
        <Link href={`/learn/${item.concept_id}`} className="text-sm font-medium hover:underline">
          {item.concept?.name ?? `Concept ${item.concept_id}`}
        </Link>
        <p className="text-muted-foreground text-xs">
          {item.reason === "mistake" ? "After a mistake" : "Spaced review"} · {formatDue(item.due_at)}
          {item.retention_estimate != null && ` · est. retention ${Math.round(item.retention_estimate * 100)}%`}
        </p>
      </div>
      <MasteryBar p={item.mastery?.p_known ?? null} level={item.mastery?.level ?? "not_started"} />
      <Button
        size="sm"
        variant={due ? "gradient" : "outline"}
        loading={start.isPending}
        onClick={() => start.mutate({ mode: "revision", concept_ids: [item.concept_id] })}
      >
        Revise
      </Button>
    </li>
  );
}

export function RevisionPage() {
  const queue = useQuery({ queryKey: ["revision"], queryFn: learning.revision });
  const start = useStartSession();
  if (queue.isLoading) return <LoadingState />;
  if (queue.isError || !queue.data) return <ErrorState onRetry={() => void queue.refetch()} />;
  const { due, upcoming } = queue.data;

  return (
    <>
      <PageHeader
        title="Revision centre"
        description="Spaced repetition scheduled from your own answers: concepts you miss come back sooner, ones you know come back later."
        actions={
          due.length > 0 && (
            <Button variant="gradient" loading={start.isPending} onClick={() => start.mutate({ mode: "revision" })}>
              <RotateCcw /> Revise all due ({due.length})
            </Button>
          )
        }
      />
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Due now {due.length > 0 && <Badge variant="warning">{due.length}</Badge>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {due.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="Nothing due"
              description={
                upcoming.length
                  ? "You're up to date. The next review is listed below."
                  : "Revision is scheduled once you start practising."
              }
              className="py-6"
            />
          ) : (
            <ul className="divide-y">
              {due.map((i) => (
                <RevisionRow key={i.concept_id} item={i} due />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
      {upcoming.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Coming up</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y">
              {upcoming.map((i) => (
                <RevisionRow key={i.concept_id} item={i} due={false} />
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </>
  );
}

// ── Weak topics ──────────────────────────────────────────────────────────────

export function WeakTopicsPage() {
  const weak = useQuery({ queryKey: ["weak"], queryFn: learning.weak });
  const start = useStartSession();
  if (weak.isLoading) return <LoadingState />;
  if (weak.isError || !weak.data) return <ErrorState onRetry={() => void weak.refetch()} />;
  const list = weak.data;

  return (
    <>
      <PageHeader
        title="Weak topics"
        description="Concepts where your mastery estimate is low, weakest first. Each one shows the evidence behind it."
        actions={
          list.length > 0 && (
            <Button
              variant="gradient"
              loading={start.isPending}
              onClick={() => start.mutate({ mode: "adaptive", concept_ids: list.slice(0, 10).map((c) => c.id) })}
            >
              <Target /> Practise these
            </Button>
          )
        }
      />
      {list.length === 0 ? (
        <Card>
          <EmptyState
            icon={Activity}
            title="No weak topics"
            description="Either you're doing well, or you haven't practised enough yet for an estimate."
            action={
              <Button asChild variant="outline" size="sm">
                <Link href="/practice">Practise</Link>
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {list.map((c) => (
            <Card key={c.id}>
              <CardContent className="space-y-3 p-5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <Link href={`/learn/${c.id}`} className="font-medium hover:underline">
                      {c.name}
                    </Link>
                    <p className="text-muted-foreground text-xs">
                      {c.subject.name} · {c.chapter.name}
                    </p>
                  </div>
                  <LevelBadge level={c.level} />
                </div>
                <MasteryBar p={c.p_known} level={c.level} />
                <p className="text-muted-foreground text-xs">
                  {c.correct} of {c.attempts} correct · last practised {formatRelative(c.last_practiced_at)}
                </p>
                {c.weak_prerequisites.length > 0 && (
                  <p className="bg-warning/5 rounded-lg px-3 py-2 text-xs">
                    Builds on weak:{" "}
                    {c.weak_prerequisites.map((p, i) => (
                      <span key={p.id}>
                        {i > 0 && ", "}
                        <Link href={`/learn/${p.id}`} className="font-medium underline">
                          {p.name}
                        </Link>
                      </span>
                    ))}
                  </p>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  loading={
                    start.isPending &&
                    start.variables?.concept_ids?.[0] === c.id &&
                    start.variables.concept_ids.length === 1
                  }
                  onClick={() => start.mutate({ mode: "adaptive", concept_ids: [c.id] })}
                >
                  Practise
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

// ── Error notebook ───────────────────────────────────────────────────────────

const CATEGORIES: { id: MistakeCategory; label: string }[] = [
  { id: "uncategorised", label: "Uncategorised" },
  { id: "concept", label: "Didn't understand the concept" },
  { id: "calculation", label: "Calculation slip" },
  { id: "misread", label: "Misread the question" },
  { id: "time", label: "Ran out of time" },
  { id: "guess", label: "Guessed" },
];

function NotebookCard({ entry }: { entry: NotebookEntry }) {
  const qc = useQueryClient();
  const start = useStartSession();
  const [note, setNote] = useState(entry.note ?? "");
  const refresh = () => void qc.invalidateQueries({ queryKey: ["notebook"] });
  const update = useMutation({
    mutationFn: (body: Parameters<typeof learning.updateEntry>[1]) => learning.updateEntry(entry.id, body),
    onSuccess: refresh,
    onError: (e) => toast.error(errMsg(e)),
  });
  const remove = useMutation({
    mutationFn: () => learning.deleteEntry(entry.id),
    onSuccess: () => {
      toast.success("Removed from your notebook");
      refresh();
    },
    onError: (e) => toast.error(errMsg(e)),
  });
  const q = entry.question;

  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant={entry.status === "resolved" ? "success" : entry.source === "mistake" ? "destructive" : "blue"}
          >
            {entry.status === "resolved"
              ? "Resolved"
              : entry.source === "mistake"
                ? `Wrong ${entry.times_wrong}×`
                : "Saved"}
          </Badge>
          <Badge variant="outline">{TYPE_LABEL[q.type]}</Badge>
          {q.concepts.map((c) => (
            <Badge key={c.id} variant="muted">
              {c.name}
            </Badge>
          ))}
          <span className="text-muted-foreground ml-auto text-xs">{formatRelative(entry.updated_at)}</span>
        </div>

        <QuestionView
          idPrefix={entry.id}
          type={q.type}
          stem={q.stem}
          content={q.content}
          response={entry.your_answer ?? {}}
          reveal={entry.correct_answer}
        />
        {entry.solution && (
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-muted-foreground mb-1 text-xs font-semibold tracking-wide uppercase">Solution</p>
            <Markdown>{entry.solution}</Markdown>
          </div>
        )}

        <div className="grid gap-3 border-t pt-4 sm:grid-cols-[14rem_1fr]">
          <label className="flex flex-col gap-1.5 text-xs font-medium">
            Why did I get it wrong?
            <Select
              value={entry.category}
              onChange={(e) => update.mutate({ category: e.target.value as MistakeCategory })}
              aria-label="Mistake category"
            >
              {CATEGORIES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </Select>
          </label>
          <label className="flex flex-col gap-1.5 text-xs font-medium">
            Note to self
            <Input
              value={note}
              maxLength={1000}
              placeholder="e.g. remember the sign when the ball bounces back"
              onChange={(e) => setNote(e.target.value)}
              onBlur={() => note !== (entry.note ?? "") && update.mutate({ note })}
            />
          </label>
        </div>
        <div className="flex flex-wrap gap-2">
          {entry.can_reattempt && (
            <Button
              size="sm"
              variant="gradient"
              loading={start.isPending}
              onClick={() => start.mutate({ mode: "review", question_ids: [entry.question_id] })}
            >
              <RotateCcw /> Reattempt
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            loading={update.isPending && update.variables?.status !== undefined}
            onClick={() => update.mutate({ status: entry.status === "open" ? "resolved" : "open" })}
          >
            <CheckCircle2 /> {entry.status === "open" ? "Mark resolved" : "Reopen"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-destructive"
            loading={remove.isPending}
            onClick={() => remove.mutate()}
          >
            <Trash2 /> Remove
          </Button>
          {entry.times_right_since > 0 && (
            <span className="text-success self-center text-xs">
              Right {entry.times_right_since}× since your last mistake
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function ErrorNotebookPage() {
  const [status, setStatus] = useState("open");
  const [category, setCategory] = useState("");
  const entries = useQuery({
    queryKey: ["notebook", status, category],
    queryFn: () => learning.notebook({ status, category }),
  });
  const start = useStartSession();
  const retryable = (entries.data ?? []).filter((e) => e.can_reattempt && e.status === "open").slice(0, 30);

  return (
    <>
      <PageHeader
        title="Error notebook"
        description="Every mistake is saved here automatically. Review the solution, note what went wrong, and try again."
        actions={
          retryable.length > 1 && (
            <Button
              variant="gradient"
              loading={start.isPending}
              onClick={() => start.mutate({ mode: "review", question_ids: retryable.map((e) => e.question_id) })}
            >
              <RotateCcw /> Reattempt all ({retryable.length})
            </Button>
          )
        }
      />
      <div className="mb-4 flex flex-wrap gap-2">
        <Select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
          <option value="">All</option>
        </Select>
        <Select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category">
          <option value="">Any reason</option>
          {CATEGORIES.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </Select>
      </div>
      {entries.isLoading ? (
        <LoadingState />
      ) : entries.isError ? (
        <ErrorState onRetry={() => void entries.refetch()} />
      ) : !entries.data?.length ? (
        <Card>
          <EmptyState
            icon={NotebookPen}
            title={status === "resolved" ? "Nothing resolved yet" : "No mistakes saved"}
            description="Questions you get wrong in practice appear here, along with any you save as difficult."
          />
        </Card>
      ) : (
        <div className="space-y-4">
          {entries.data.map((e) => (
            <NotebookCard key={e.id} entry={e} />
          ))}
        </div>
      )}
    </>
  );
}
