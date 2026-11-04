"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  BookmarkPlus,
  CheckCircle2,
  Info,
  Lightbulb,
  NotebookPen,
  Pause,
  Play,
  Timer,
  TrendingDown,
  TrendingUp,
  XCircle,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ErrorState, LoadingState } from "@/components/feedback/states";
import { Markdown } from "@/components/questions/markdown";
import { isComplete, QuestionView, TYPE_LABEL } from "@/components/questions/question-view";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";
import type { Delivery, Feedback, Response } from "@/types/learning";
import { learning } from "./api";

type Active = Extract<Delivery, { finished: false }>;

const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong.");

function Elapsed({ since, stopped }: { since: string; stopped: boolean }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (stopped) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [stopped]);
  const s = Math.max(0, Math.floor((now - new Date(since).getTime()) / 1000));
  return (
    <span
      className="text-muted-foreground inline-flex items-center gap-1 text-xs tabular-nums"
      aria-label="Time on this question"
    >
      <Timer className="size-3.5" aria-hidden /> {Math.floor(s / 60)}:{String(s % 60).padStart(2, "0")}
    </span>
  );
}

function FeedbackPanel({ fb }: { fb: Feedback }) {
  const meta = {
    correct: { icon: CheckCircle2, title: "Correct", cls: "border-success/30 bg-success/5 [&_svg]:text-success" },
    partial: { icon: Info, title: "Partly correct", cls: "border-warning/30 bg-warning/5 [&_svg]:text-warning" },
    incorrect: {
      icon: XCircle,
      title: "Not quite",
      cls: "border-destructive/30 bg-destructive/5 [&_svg]:text-destructive",
    },
    ungraded: { icon: Info, title: "Answer saved", cls: "border-accent/30 bg-accent/5 [&_svg]:text-accent" },
  }[fb.evaluation];
  return (
    <div className={cn("rounded-xl border p-4", meta.cls)} role="status" aria-live="polite">
      <p className="flex items-center gap-2 font-semibold">
        <meta.icon className="size-5" aria-hidden /> {meta.title}
        {fb.evaluation === "partial" && (
          <span className="text-muted-foreground text-sm font-normal">({Math.round(fb.score * 100)}%)</span>
        )}
      </p>
      {fb.evaluation === "ungraded" && (
        <p className="text-muted-foreground mt-1 text-sm">
          Written answers aren&apos;t marked automatically. Compare yours with the model answer.
        </p>
      )}
      {fb.solution && (
        <div className="mt-3 border-t border-current/10 pt-3">
          <p className="text-muted-foreground mb-1 text-xs font-semibold tracking-wide uppercase">Solution</p>
          <Markdown>{fb.solution}</Markdown>
        </div>
      )}
      {fb.mastery_changes.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-current/10 pt-3 text-sm">
          {fb.mastery_changes.map((m) => {
            const up = m.after >= m.before;
            const Icon = up ? TrendingUp : TrendingDown;
            return (
              <li key={m.concept_id} className="flex items-center gap-2">
                <Icon className={cn("size-4", up ? "text-success" : "text-destructive")} aria-hidden />
                <span className="flex-1">{m.name}</span>
                <span className="text-muted-foreground tabular-nums">
                  {Math.round(m.before * 100)}% →{" "}
                  <strong className="text-foreground">{Math.round(m.after * 100)}%</strong>
                </span>
              </li>
            );
          })}
        </ul>
      )}
      {fb.mastery_pending && <p className="text-muted-foreground mt-2 text-xs">Your mastery estimate is updating…</p>}
    </div>
  );
}

export function PracticePlayer({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const qc = useQueryClient();
  const [delivery, setDelivery] = useState<Active | null>(null);
  const [response, setResponse] = useState<Response>({});
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [hints, setHints] = useState<string[]>([]);
  const keys = useRef(new Map<string, string>()); // session question → idempotency key (stable across retries)

  const session = useQuery({ queryKey: ["session", sessionId], queryFn: () => learning.session(sessionId) });
  const status = session.data?.status;

  const next = useMutation({
    mutationFn: () => learning.next(sessionId),
    onSuccess: (d) => {
      if (d.finished) {
        void qc.invalidateQueries({ queryKey: ["dashboard"] });
        router.replace(`/practice/${sessionId}/report${d.exhausted ? "?exhausted=1" : ""}`);
        return;
      }
      setDelivery(d);
      setResponse({});
      setFeedback(null);
      setHints(d.question.hints);
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  const submit = useMutation({
    mutationFn: () => {
      const sq = delivery!.session_question_id;
      if (!keys.current.has(sq)) keys.current.set(sq, crypto.randomUUID());
      return learning.submit(sq, response, keys.current.get(sq)!);
    },
    onSuccess: (fb) => {
      setFeedback(fb);
      qc.setQueryData(["session", sessionId], fb.session);
      void qc.invalidateQueries({ queryKey: ["dashboard"] });
      void qc.invalidateQueries({ queryKey: ["my-curriculum"] });
    },
    onError: (e) => toast.error(`${errMsg(e)} Your answer is kept — press Submit to retry.`),
  });

  const hint = useMutation({
    mutationFn: () => learning.hint(sessionId, delivery!.session_question_id),
    onSuccess: (r) => setHints(r.hints),
    onError: (e) => toast.error(errMsg(e)),
  });

  const started = useRef(false);

  const lifecycle = useMutation({
    mutationFn: (action: "pause" | "resume" | "complete") => learning.lifecycle(sessionId, action),
    onSuccess: (s, action) => {
      qc.setQueryData(["session", sessionId], s);
      void qc.invalidateQueries({ queryKey: ["sessions"] });
      if (action === "pause") router.push("/practice");
      if (action === "complete") router.replace(`/practice/${sessionId}/report`);
      if (action === "resume") {
        started.current = true; // the load effect must not fetch a second time
        next.mutate();
      }
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  const save = useMutation({
    mutationFn: () => learning.saveToNotebook(delivery!.question.question_id),
    onSuccess: () => toast.success("Saved to your error notebook"),
    onError: (e) => toast.error(errMsg(e)),
  });

  // Load (or recover) the current question once the session is known to be active.
  useEffect(() => {
    if (!status || started.current) return;
    if (status === "completed") return router.replace(`/practice/${sessionId}/report`);
    if (status === "active") {
      started.current = true;
      next.mutate();
    }
  }, [status, sessionId, router, next]);

  const canSubmit = !!delivery && !feedback && isComplete(delivery.question.type, delivery.question.content, response);
  const finished = feedback?.session.status === "completed";

  const onKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key !== "Enter" || e.shiftKey || (e.target as HTMLElement)?.tagName === "TEXTAREA") return;
      if (feedback && !next.isPending) {
        e.preventDefault();
        if (finished) router.replace(`/practice/${sessionId}/report`);
        else next.mutate();
      } else if (canSubmit && !submit.isPending) {
        e.preventDefault();
        submit.mutate();
      }
    },
    [feedback, finished, canSubmit, next, submit, router, sessionId],
  );
  useEffect(() => {
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onKey]);

  if (session.isLoading) return <LoadingState />;
  if (session.isError || !session.data)
    return <ErrorState message={errMsg(session.error)} onRetry={() => void session.refetch()} />;
  const s = feedback?.session ?? delivery?.session ?? session.data;

  if (s.status === "paused") {
    return (
      <Card className="mx-auto max-w-lg p-8 text-center">
        <Pause className="text-muted-foreground mx-auto size-8" aria-hidden />
        <h1 className="mt-3 text-xl font-semibold">{s.title}</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Paused after {s.answered_count} of {s.target_count} questions. Pick up exactly where you left off.
        </p>
        <Button
          className="mt-5"
          variant="gradient"
          loading={lifecycle.isPending}
          onClick={() => lifecycle.mutate("resume")}
        >
          <Play /> Resume
        </Button>
      </Card>
    );
  }

  const q = delivery?.question;
  const progress = Math.round((s.answered_count / s.target_count) * 100);

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold">{s.title}</p>
          <p className="text-muted-foreground text-xs">
            {s.mode === "diagnostic"
              ? "Diagnostic"
              : s.mode === "review"
                ? "Mistake review"
                : s.mode === "revision"
                  ? "Revision"
                  : "Adaptive practice"}{" "}
            · {s.answered_count} of {s.target_count} answered · {s.correct_count} correct
          </p>
        </div>
        <Button variant="ghost" size="sm" disabled={lifecycle.isPending} onClick={() => lifecycle.mutate("pause")}>
          <Pause /> Pause
        </Button>
        {s.answered_count > 0 && !finished && (
          <Button variant="ghost" size="sm" disabled={lifecycle.isPending} onClick={() => lifecycle.mutate("complete")}>
            Finish now
          </Button>
        )}
      </div>
      <div
        className="bg-muted mb-6 h-1.5 overflow-hidden rounded-full"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="bg-brand-gradient h-full transition-all" style={{ width: `${progress}%` }} />
      </div>

      {!q ? (
        <LoadingState label="Choosing your next question…" />
      ) : (
        <Card>
          <CardContent className="space-y-6 p-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="muted">Q{delivery!.position}</Badge>
              <Badge variant="outline">{TYPE_LABEL[q.type]}</Badge>
              <Badge variant="outline">Difficulty {q.difficulty}/5</Badge>
              {q.concepts.map((c) => (
                <Badge key={c.id} variant="blue">
                  {c.name}
                </Badge>
              ))}
              <span className="ml-auto">
                <Elapsed since={delivery!.delivered_at} stopped={!!feedback} />
              </span>
            </div>

            {delivery!.why && (
              <p className="text-muted-foreground bg-muted/50 flex items-start gap-2 rounded-lg px-3 py-2 text-xs">
                <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                <span>
                  <strong className="text-foreground font-medium">Why this question:</strong> {delivery!.why}
                </span>
              </p>
            )}

            <QuestionView
              key={delivery!.session_question_id}
              idPrefix={delivery!.session_question_id}
              type={q.type}
              stem={q.stem}
              content={q.content}
              response={response}
              onChange={feedback ? undefined : setResponse}
              reveal={feedback?.correct_answer ?? null}
            />

            {hints.length > 0 && (
              <div className="space-y-2">
                {hints.map((h, i) => (
                  <Alert key={i} variant="warning">
                    <Lightbulb />
                    <Markdown>{`**Hint ${i + 1}:** ${h}`}</Markdown>
                  </Alert>
                ))}
              </div>
            )}

            {feedback && <FeedbackPanel fb={feedback} />}

            <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
              <div className="flex gap-2">
                {!feedback && q.hints_available > hints.length && (
                  <Button variant="outline" size="sm" loading={hint.isPending} onClick={() => hint.mutate()}>
                    <Lightbulb /> Hint ({hints.length + 1} of {q.hints_available})
                  </Button>
                )}
                {feedback?.evaluation === "correct" && (
                  <Button variant="ghost" size="sm" loading={save.isPending} onClick={() => save.mutate()}>
                    <BookmarkPlus /> Save as difficult
                  </Button>
                )}
                {(feedback?.evaluation === "incorrect" || feedback?.evaluation === "partial") && (
                  <span className="text-muted-foreground inline-flex items-center gap-1.5 text-xs">
                    <NotebookPen className="size-3.5" aria-hidden /> Added to your error notebook
                  </span>
                )}
              </div>
              {!feedback ? (
                <Button
                  variant="gradient"
                  disabled={!canSubmit}
                  loading={submit.isPending}
                  onClick={() => submit.mutate()}
                >
                  Submit answer
                </Button>
              ) : finished ? (
                <Button variant="gradient" onClick={() => router.replace(`/practice/${sessionId}/report`)}>
                  See your report <ArrowRight />
                </Button>
              ) : (
                <Button variant="gradient" loading={next.isPending} onClick={() => next.mutate()}>
                  Next question <ArrowRight />
                </Button>
              )}
            </div>
            {hints.length > 0 && !feedback && (
              <p className="text-muted-foreground -mt-3 text-right text-xs">
                Using hints counts as weaker evidence of mastery.
              </p>
            )}
          </CardContent>
        </Card>
      )}
      <p className="text-muted-foreground mt-3 text-center text-xs">Press Enter to submit or continue.</p>
    </div>
  );
}
