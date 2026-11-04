"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ClipboardCheck, Search, Target } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { LevelBadge, MasteryBar } from "@/components/questions/mastery-bar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { TreeChapter } from "@/types/learning";
import { learning } from "./api";
import { useStartSession } from "./use-start-session";

function ChapterCard({ chapter, defaultOpen }: { chapter: TreeChapter; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const start = useStartSession();
  const concepts = chapter.topics.flatMap((t) => t.concepts);
  const total = chapter.concept_count ?? concepts.length;
  const done = chapter.completed_count ?? concepts.filter((c) => c.level === "mastered").length;
  const practisable = chapter.practisable ?? concepts.some((c) => c.question_count > 0);
  const started = concepts.some((c) => c.attempts > 0);

  return (
    <Card>
      <div className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center">
        <button
          className="flex min-w-0 flex-1 items-center gap-3 text-left"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
        >
          <ChevronDown
            className={cn("text-muted-foreground size-4 shrink-0 transition-transform", !open && "-rotate-90")}
          />
          <div className="min-w-0">
            <p className="font-semibold">{chapter.name}</p>
            <p className="text-muted-foreground text-xs">
              {done} of {total} concepts mastered
            </p>
          </div>
        </button>
        <div className="flex gap-2 pl-7 sm:pl-0">
          {practisable ? (
            <>
              {!started && (
                <Button
                  size="sm"
                  variant="outline"
                  loading={start.isPending && start.variables?.mode === "diagnostic"}
                  onClick={() => start.mutate({ mode: "diagnostic", chapter_id: chapter.id })}
                >
                  <ClipboardCheck /> Diagnostic
                </Button>
              )}
              <Button
                size="sm"
                variant="gradient"
                loading={start.isPending && start.variables?.mode === "adaptive"}
                onClick={() => start.mutate({ mode: "adaptive", chapter_id: chapter.id })}
              >
                <Target /> Practise
              </Button>
            </>
          ) : (
            <Badge variant="muted">No questions yet</Badge>
          )}
        </div>
      </div>
      {open && (
        <div className="border-t px-5 py-3">
          {chapter.topics.map((t) => (
            <div key={t.id} className="py-2">
              {chapter.topics.length > 1 && (
                <p className="text-muted-foreground mb-1 text-xs font-medium tracking-wide uppercase">{t.name}</p>
              )}
              <ul className="divide-y">
                {t.concepts.map((c) => (
                  <li key={c.id} className="grid items-center gap-2 py-2.5 sm:grid-cols-[1fr_9rem_7rem]">
                    <Link href={`/learn/${c.id}`} className="text-sm font-medium hover:underline">
                      {c.name}
                    </Link>
                    <MasteryBar p={c.p_known} level={c.level} />
                    <div className="sm:text-right">
                      <LevelBadge level={c.level} />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export function CurriculumPage() {
  const tree = useQuery({ queryKey: ["my-curriculum"], queryFn: learning.myCurriculum });
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 250);
    return () => clearTimeout(t);
  }, [q]);
  const search = useQuery({
    queryKey: ["concept-search", debounced],
    queryFn: () => learning.search(debounced),
    enabled: debounced.length >= 2,
  });

  if (tree.isLoading) return <LoadingState />;
  if (tree.isError || !tree.data) return <ErrorState onRetry={() => void tree.refetch()} />;
  const t = tree.data;
  const chapters = t.subjects.flatMap((s) => s.chapters);
  // Open the chapter the student is working on, or else the first one with questions.
  const openId = (
    chapters.find((c) => c.topics.some((tp) => tp.concepts.some((x) => x.attempts > 0))) ??
    chapters.find((c) => c.practisable !== false)
  )?.id;

  return (
    <>
      <PageHeader
        title="My curriculum"
        description={
          <>
            {t.board.name}
            {t.grade && ` · ${t.grade.name}`} · syllabus {t.version}{" "}
            {t.is_sample && <Badge variant="warning">Sample content</Badge>}
          </>
        }
        actions={
          <Button asChild variant="outline">
            <Link href="/profile">Change</Link>
          </Button>
        }
      />

      <div className="relative mb-6 max-w-md">
        <Search className="text-muted-foreground absolute top-1/2 left-3 size-4 -translate-y-1/2" aria-hidden />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search concepts"
          className="pl-9"
          aria-label="Search concepts"
        />
        {debounced.length >= 2 && (
          <Card className="absolute top-full z-20 mt-1 w-full p-1 shadow-lg">
            {search.isLoading ? (
              <LoadingState className="py-4" />
            ) : search.data?.length ? (
              search.data.map((c) => (
                <Link key={c.id} href={`/learn/${c.id}`} className="hover:bg-muted block rounded-md px-3 py-2 text-sm">
                  <span className="font-medium">{c.name}</span>
                  <span className="text-muted-foreground block text-xs">
                    {c.subject.name} · {c.chapter.name}
                  </span>
                </Link>
              ))
            ) : (
              <p className="text-muted-foreground px-3 py-2 text-sm">No concepts match “{debounced}”.</p>
            )}
          </Card>
        )}
      </div>

      {t.subjects.length === 0 && (
        <EmptyState title="No subjects selected" description="Choose subjects from your profile." />
      )}
      {t.subjects.map((s) => (
        <section key={s.id} className="mb-8">
          <h2 className="mb-3 text-lg font-semibold">{s.name}</h2>
          <div className="space-y-3">
            {s.chapters.map((c) => (
              <ChapterCard key={c.id} chapter={c} defaultOpen={c.id === openId} />
            ))}
          </div>
        </section>
      ))}
    </>
  );
}
