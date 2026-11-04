"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, BookOpen, Bot, Lock, Target } from "lucide-react";
import Link from "next/link";
import { ErrorState, LoadingState } from "@/components/feedback/states";
import { Markdown } from "@/components/questions/markdown";
import { LevelBadge, MasteryBar } from "@/components/questions/mastery-bar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatRelative } from "@/lib/utils";
import { ApiError } from "@/services/api";
import type { ConceptRef, Mastery } from "@/types/learning";
import { learning } from "./api";
import { useStartSession } from "./use-start-session";

function ConceptLink({ c }: { c: ConceptRef & Mastery }) {
  return (
    <li>
      <Link href={`/learn/${c.id}`} className="hover:bg-muted/60 -mx-2 block rounded-lg px-2 py-2">
        <span className="flex items-center justify-between gap-2 text-sm font-medium">
          {c.name} <LevelBadge level={c.level} />
        </span>
        <MasteryBar p={c.p_known} level={c.level} className="mt-1.5" />
      </Link>
    </li>
  );
}

export function ConceptPage({ id }: { id: number }) {
  const concept = useQuery({ queryKey: ["concept", id], queryFn: () => learning.concept(id) });
  const start = useStartSession();

  if (concept.isLoading) return <LoadingState />;
  if (concept.isError || !concept.data)
    return (
      <ErrorState
        message={concept.error instanceof ApiError ? concept.error.message : undefined}
        onRetry={() => void concept.refetch()}
      />
    );
  const c = concept.data;
  const weakPrereqs = c.prerequisites.filter((p) => p.level === "weak" || p.level === "not_started");

  return (
    <>
      <Link
        href="/curriculum"
        className="text-muted-foreground hover:text-foreground mb-4 inline-flex items-center gap-1.5 text-sm"
      >
        <ArrowLeft className="size-4" /> {c.subject.name} · {c.chapter.name}
      </Link>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{c.name}</h1>
          <p className="text-muted-foreground mt-1 text-sm">{c.topic.name}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link href={`/tutor?concept=${c.id}&mode=teach`}>
              <Bot /> Ask the tutor
            </Link>
          </Button>
          <Button
            variant="gradient"
            disabled={c.question_count === 0}
            loading={start.isPending}
            onClick={() => start.mutate({ mode: "adaptive", concept_ids: [c.id] })}
          >
            <Target /> Practise this concept
          </Button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
        <div className="space-y-4">
          {weakPrereqs.length > 0 && (
            <Card className="border-warning/30 bg-warning/5">
              <CardContent className="flex gap-3 p-4 text-sm">
                <Lock className="text-warning mt-0.5 size-4 shrink-0" aria-hidden />
                <p>
                  This builds on{" "}
                  {weakPrereqs.map((p, i) => (
                    <span key={p.id}>
                      {i > 0 && (i === weakPrereqs.length - 1 ? " and " : ", ")}
                      <Link href={`/learn/${p.id}`} className="font-medium underline">
                        {p.name}
                      </Link>
                    </span>
                  ))}
                  . Practice will bring those in when you need them.
                </p>
              </CardContent>
            </Card>
          )}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="text-primary size-4" /> Learn
              </CardTitle>
            </CardHeader>
            <CardContent>
              {c.description ? (
                <Markdown className="text-[15px]">{c.description}</Markdown>
              ) : (
                <p className="text-muted-foreground text-sm">No explanation has been written for this concept yet.</p>
              )}
            </CardContent>
          </Card>
          {c.unlocks.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>What this unlocks</CardTitle>
                <CardDescription>Concepts that build on this one.</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1">
                  {c.unlocks.map((u) => (
                    <ConceptLink key={u.id} c={u} />
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Your mastery <LevelBadge level={c.level} />
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <MasteryBar p={c.p_known} level={c.level} />
              <dl className="text-muted-foreground grid grid-cols-2 gap-y-1">
                <dt>Answered</dt>
                <dd className="text-foreground text-right">{c.attempts}</dd>
                <dt>Correct</dt>
                <dd className="text-foreground text-right">{c.correct}</dd>
                <dt>Last practised</dt>
                <dd className="text-foreground text-right">{formatRelative(c.last_practiced_at)}</dd>
                <dt>Questions available</dt>
                <dd className="text-foreground text-right">{c.question_count}</dd>
              </dl>
              {c.attempts > 0 && (
                <p className="text-muted-foreground text-xs">
                  Estimate confidence {Math.round(c.confidence * 100)}% — it firms up as you answer more.
                </p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Prerequisites</CardTitle>
            </CardHeader>
            <CardContent>
              {c.prerequisites.length === 0 ? (
                <p className="text-muted-foreground text-sm">None — a good place to start.</p>
              ) : (
                <ul className="space-y-1">
                  {c.prerequisites.map((p) => (
                    <ConceptLink key={p.id} c={p} />
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
          {c.question_count === 0 && (
            <Badge variant="muted" className="w-full justify-center py-1.5">
              No practice questions for this concept yet
            </Badge>
          )}
        </div>
      </div>
    </>
  );
}

export function LearnHome() {
  const recs = useQuery({ queryKey: ["recommendations"], queryFn: learning.recommendations });
  const tree = useQuery({ queryKey: ["my-curriculum"], queryFn: learning.myCurriculum });
  if (recs.isLoading || tree.isLoading) return <LoadingState />;
  if (tree.isError || !tree.data) return <ErrorState onRetry={() => void tree.refetch()} />;
  const concepts = tree.data.subjects.flatMap((s) =>
    s.chapters.flatMap((ch) =>
      ch.topics.flatMap((t) => t.concepts.map((c) => ({ ...c, chapter: ch.name, subject: s.name }))),
    ),
  );
  const next = (recs.data ?? []).filter((r) => r.type === "practice_concept" && r.concept_id);
  const ids = new Set(next.map((r) => r.concept_id));

  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Learn</h1>
        <p className="text-muted-foreground mt-1 text-sm">Read a concept, then practise it straight away.</p>
      </div>
      {next.length > 0 && (
        <section className="mb-8">
          <h2 className="text-muted-foreground mb-3 text-sm font-semibold tracking-wide uppercase">
            Recommended for you
          </h2>
          <div className="grid gap-3 md:grid-cols-3">
            {next.map((r) => {
              const c = concepts.find((x) => x.id === r.concept_id);
              return (
                <Link key={r.concept_id} href={`/learn/${r.concept_id}`}>
                  <Card className="hover:border-primary/40 h-full p-4 transition-colors">
                    <p className="font-medium">{c?.name ?? r.title}</p>
                    <p className="text-muted-foreground mt-1 text-xs">{r.reason}</p>
                    {c && <MasteryBar p={c.p_known} level={c.level} className="mt-3" />}
                  </Card>
                </Link>
              );
            })}
          </div>
        </section>
      )}
      <section>
        <h2 className="text-muted-foreground mb-3 text-sm font-semibold tracking-wide uppercase">All concepts</h2>
        <Card>
          <ul className="divide-y">
            {concepts
              .filter((c) => !ids.has(c.id))
              .map((c) => (
                <li key={c.id}>
                  <Link href={`/learn/${c.id}`} className="hover:bg-muted/50 flex items-center gap-4 px-5 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{c.name}</p>
                      <p className="text-muted-foreground text-xs">
                        {c.subject} · {c.chapter}
                      </p>
                    </div>
                    <MasteryBar p={c.p_known} level={c.level} className="hidden w-40 sm:flex" />
                    <ArrowRight className="text-muted-foreground size-4" aria-hidden />
                  </Link>
                </li>
              ))}
          </ul>
        </Card>
      </section>
    </>
  );
}
