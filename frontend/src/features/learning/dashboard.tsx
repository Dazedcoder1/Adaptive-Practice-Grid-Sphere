"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CircleCheck, Clock, Flame, Gauge, Play, RotateCcw, Sparkles, Target } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { StatCard } from "@/components/dashboard/stat-card";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { formatDuration, MasteryBar } from "@/components/questions/mastery-bar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDue, formatRelative } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";
import type { Recommendation } from "@/types/learning";
import { learning } from "./api";
import { useStartSession } from "./use-start-session";

const pct = (v: number | null) => (v == null ? "—" : `${Math.round(v * 100)}%`);

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export function RecommendationAction({ rec }: { rec: Recommendation }) {
  const router = useRouter();
  const start = useStartSession();
  const go = () => {
    switch (rec.type) {
      case "continue_session":
        return router.push(`/practice/${rec.session_id}`);
      case "onboarding":
        return router.push("/onboarding");
      case "revision":
        return router.push("/revision");
      case "diagnostic":
        return start.mutate({ mode: "diagnostic", chapter_id: rec.chapter_id });
      case "practice_concept":
        return start.mutate({ mode: "adaptive", concept_ids: [rec.concept_id!] });
    }
  };
  return (
    <Button size="sm" variant="outline" loading={start.isPending} onClick={go}>
      {rec.type === "continue_session" ? "Resume" : "Start"} <ArrowRight />
    </Button>
  );
}

export function StudentDashboard() {
  const user = useAuthStore((s) => s.user);
  const dash = useQuery({ queryKey: ["dashboard"], queryFn: learning.dashboard });
  const first = user?.display_name?.split(" ")[0] ?? "there";

  if (dash.isLoading) return <LoadingState />;
  if (dash.isError || !dash.data) return <ErrorState onRetry={() => void dash.refetch()} />;
  const d = dash.data;
  const [top, ...more] = d.recommendations;

  return (
    <>
      <PageHeader
        title={`${greeting()}, ${first}`}
        description={
          d.has_activity
            ? `${d.concepts_practised} of ${d.concepts_total} concepts practised · ${d.concepts_mastered} mastered`
            : "Your learning journey starts here."
        }
      />

      {top && (
        <Card className="mb-6 overflow-hidden">
          <div className="bg-soft-gradient flex flex-col gap-4 p-6 sm:flex-row sm:items-center">
            <div className="bg-brand-gradient flex size-12 shrink-0 items-center justify-center rounded-2xl text-white">
              <Sparkles className="size-6" aria-hidden />
            </div>
            <div className="flex-1">
              <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">Recommended next</p>
              <h2 className="mt-0.5 font-semibold">{top.title}</h2>
              <p className="text-muted-foreground mt-0.5 text-sm">{top.reason}</p>
            </div>
            <RecommendationAction rec={top} />
          </div>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          label="Average mastery"
          value={pct(d.average_mastery)}
          icon={Gauge}
          hint="Across concepts you've practised"
        />
        <StatCard label="Questions attempted" value={d.questions_attempted.toLocaleString("en-IN")} icon={Target} />
        <StatCard label="Accuracy" value={pct(d.accuracy)} icon={CircleCheck} />
        <StatCard label="Study time" value={d.study_seconds ? formatDuration(d.study_seconds) : "—"} icon={Clock} />
        <StatCard
          label="Learning streak"
          value={`${d.streak_days} ${d.streak_days === 1 ? "day" : "days"}`}
          icon={Flame}
          hint={
            d.active_today ? "You've practised today" : d.streak_days ? "Practise today to keep it going" : undefined
          }
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Weak topics</CardTitle>
            <CardDescription>Lowest mastery estimates first.</CardDescription>
          </CardHeader>
          <CardContent>
            {d.weak_concepts.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                {d.has_activity ? "Nothing weak right now — keep practising." : "Practise to find out where to focus."}
              </p>
            ) : (
              <ul className="space-y-3">
                {d.weak_concepts.slice(0, 4).map((c) => (
                  <li key={c.id}>
                    <Link href={`/learn/${c.id}`} className="text-sm font-medium hover:underline">
                      {c.name}
                    </Link>
                    <MasteryBar p={c.p_known} level={c.level} className="mt-1" />
                  </li>
                ))}
              </ul>
            )}
            {d.weak_concepts.length > 0 && (
              <Button asChild variant="link" className="mt-2 h-auto p-0">
                <Link href="/weak-topics">All weak topics</Link>
              </Button>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Upcoming revision {d.revision_due > 0 && <Badge variant="warning">{d.revision_due} due</Badge>}
            </CardTitle>
            <CardDescription>Scheduled from your own answers.</CardDescription>
          </CardHeader>
          <CardContent>
            {d.revision_due === 0 && d.revision_upcoming.length === 0 ? (
              <p className="text-muted-foreground text-sm">Revision appears here after you practise.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {d.revision_upcoming.slice(0, 4).map((r) => (
                  <li key={r.concept_id} className="flex items-center justify-between gap-2">
                    <span className="truncate">{r.concept?.name ?? `Concept ${r.concept_id}`}</span>
                    <span className="text-muted-foreground shrink-0 text-xs">{formatDue(r.due_at)}</span>
                  </li>
                ))}
              </ul>
            )}
            <Button asChild variant="link" className="mt-2 h-auto p-0">
              <Link href="/revision">
                <RotateCcw /> Revision centre
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent sessions</CardTitle>
          </CardHeader>
          <CardContent>
            {d.recent_sessions.length === 0 ? (
              <EmptyState
                icon={Play}
                title="No sessions yet"
                className="py-4"
                action={
                  <Button asChild size="sm" variant="gradient">
                    <Link href="/practice">Start practising</Link>
                  </Button>
                }
              />
            ) : (
              <ul className="divide-y text-sm">
                {d.recent_sessions.slice(0, 5).map((s) => (
                  <li key={s.id} className="flex items-center justify-between gap-2 py-2">
                    <Link
                      href={s.status === "completed" ? `/practice/${s.id}/report` : `/practice/${s.id}`}
                      className="min-w-0 hover:underline"
                    >
                      <p className="truncate font-medium">{s.title}</p>
                      <p className="text-muted-foreground text-xs">
                        {s.correct_count}/{s.answered_count} correct · {formatRelative(s.last_activity_at)}
                      </p>
                    </Link>
                    {s.status !== "completed" && (
                      <Badge variant="blue">{s.status === "paused" ? "Paused" : "In progress"}</Badge>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {more.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>More recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y">
              {more.map((r, i) => (
                <li key={i} className="flex items-center justify-between gap-3 py-3">
                  <div>
                    <p className="text-sm font-medium">{r.title}</p>
                    <p className="text-muted-foreground text-xs">{r.reason}</p>
                  </div>
                  <RecommendationAction rec={r} />
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <p className="text-muted-foreground mt-6 text-xs">
        Mastery figures are estimates from the {d.model_version} knowledge model, updated after every answer.
      </p>
    </>
  );
}
