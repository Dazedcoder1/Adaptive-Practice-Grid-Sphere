"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  FileText,
  Footprints,
  HeartHandshake,
  Lightbulb,
  SearchCheck,
  SendHorizontal,
  ShieldCheck,
  Sparkles,
  Target,
  ThumbsDown,
  ThumbsUp,
  type LucideIcon,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Markdown } from "@/components/questions/markdown";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, inlineMaths } from "@/lib/utils";
import { ApiError } from "@/services/api";
import type { Citation, TutorMessage, TutorMode, TutorReply, TutorStatus } from "@/types/tutor";
import { tutor } from "./api";

export const MODE_META: Record<TutorMode, { label: string; icon: LucideIcon; blurb: string; placeholder: string }> = {
  teach: {
    label: "Teach me",
    icon: BookOpen,
    blurb: "Explain the idea from scratch",
    placeholder: "What would you like explained?",
  },
  hint: {
    label: "Give a hint",
    icon: Lightbulb,
    blurb: "One nudge, not the answer",
    placeholder: "Where are you stuck?",
  },
  solve: {
    label: "Solve with me",
    icon: Footprints,
    blurb: "Step by step — you do the thinking",
    placeholder: "Paste the problem or say what you've tried",
  },
  test: {
    label: "Test me",
    icon: Target,
    blurb: "Quick questions to check yourself",
    placeholder: "Say “test me” or answer the last question",
  },
  mistake: {
    label: "Find my mistake",
    icon: SearchCheck,
    blurb: "Compare your working with the solution",
    placeholder: "Describe your working or paste your answer",
  },
};
export const MODES = Object.keys(MODE_META) as TutorMode[];

export const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong.");

export function ModePicker({
  value,
  onChange,
  compact,
}: {
  value: TutorMode;
  onChange: (m: TutorMode) => void;
  compact?: boolean;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Tutor mode"
      className={cn("grid gap-2", compact ? "grid-cols-2 sm:grid-cols-5" : "grid-cols-2 lg:grid-cols-5")}
    >
      {MODES.map((m) => {
        const meta = MODE_META[m];
        const active = m === value;
        return (
          <button
            key={m}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(m)}
            className={cn(
              "focus-visible:ring-ring rounded-lg border px-3 py-2 text-left transition-colors focus-visible:ring-2 focus-visible:outline-none",
              active ? "border-primary bg-primary/5" : "hover:bg-muted bg-card",
            )}
          >
            <span className="flex items-center gap-2 text-sm font-medium">
              <meta.icon className={cn("size-4", active ? "text-primary" : "text-muted-foreground")} aria-hidden />
              {meta.label}
            </span>
            {!compact && <span className="text-muted-foreground mt-0.5 block text-xs">{meta.blurb}</span>}
          </button>
        );
      })}
    </div>
  );
}

function SourceBadge({ source }: { source: TutorMessage["source"] }) {
  if (source === "ai")
    return (
      <Badge variant="default">
        <Sparkles className="size-3" aria-hidden /> AI tutor
      </Badge>
    );
  if (source === "safety")
    return (
      <Badge variant="blue">
        <HeartHandshake className="size-3" aria-hidden /> Support
      </Badge>
    );
  return (
    <Badge variant="muted">
      <BookOpen className="size-3" aria-hidden /> From your study notes
    </Badge>
  );
}

const FLAG_NOTES: Record<string, string> = {
  answer_withheld: "The answer was held back so you can try it first.",
  counts_as_hint: "Tutor help on this question counts like a hint.",
  hint_revealed: "This hint is now shown on your question too.",
};

/** `[S1]` / `[S1, S2]` in a reply → small links that open the matching source below. */
export function linkCitations(text: string, messageId: string, valid: Set<string>) {
  return text.replace(/\[(S\d{1,2}(?:\s*,\s*S\d{1,2})*)\]/g, (whole, ids: string) => {
    const parts = ids.split(/\s*,\s*/).filter((id) => valid.has(id));
    return parts.length ? parts.map((id) => `[${id}](#${messageId}-${id})`).join(" ") : whole;
  });
}

function Sources({ citations, messageId }: { citations: Citation[]; messageId: string }) {
  if (!citations.length) return null;
  return (
    <div className="mt-3 space-y-1.5 border-t pt-3">
      <p className="text-muted-foreground text-xs font-medium">Sources</p>
      {citations.map((c) => (
        <details key={c.id} id={`${messageId}-${c.id}`} className="group bg-muted/40 rounded-md px-2.5 py-1.5 text-xs">
          <summary className="flex cursor-pointer list-none items-center gap-1.5">
            <span className="bg-primary/10 text-primary rounded px-1 font-semibold">{c.id}</span>
            <FileText className="text-muted-foreground size-3.5" aria-hidden />
            <span className="truncate font-medium">{c.heading || c.title}</span>
            <span className="text-muted-foreground truncate">
              · {c.title}
              {c.page ? ` · p. ${c.page}` : ""}
            </span>
          </summary>
          <Markdown className="text-muted-foreground mt-1.5 text-xs leading-relaxed">{inlineMaths(c.excerpt)}</Markdown>
        </details>
      ))}
    </div>
  );
}

export function MessageBubble({
  m,
  onAction,
}: {
  m: TutorMessage;
  onAction?: (a: TutorMessage["actions"][number]) => void;
}) {
  const qc = useQueryClient();
  const [helpful, setHelpful] = useState(m.helpful);
  const rate = useMutation({
    mutationFn: (v: boolean | null) => tutor.rate(m.id, v),
    onSuccess: (r) => {
      setHelpful(r.helpful);
      void qc.invalidateQueries({ queryKey: ["tutor", "conversation"] });
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  if (m.role === "student") {
    return (
      <div className="flex justify-end">
        <div className="bg-primary/10 max-w-[85%] rounded-2xl rounded-br-sm px-4 py-2.5 text-sm whitespace-pre-wrap">
          {m.content}
        </div>
      </div>
    );
  }
  const notes = m.flags.map((f) => FLAG_NOTES[f]).filter(Boolean);
  return (
    <div className="flex justify-start">
      <div className="bg-card max-w-[92%] rounded-2xl rounded-bl-sm border px-4 py-3 shadow-sm">
        <div className="mb-2 flex items-center gap-2">
          <SourceBadge source={m.source} />
          <span className="text-muted-foreground text-xs">{MODE_META[m.mode].label}</span>
        </div>
        <div
          onClick={(e) => {
            const a = (e.target as HTMLElement).closest("a");
            const id = a?.getAttribute("href")?.slice(1);
            const target = id ? document.getElementById(id) : null;
            if (target instanceof HTMLDetailsElement) {
              e.preventDefault();
              target.open = true;
              target.scrollIntoView({ block: "nearest", behavior: "smooth" });
            }
          }}
        >
          <Markdown className="[&_a]:bg-primary/10 [&_a]:text-primary [&_a]:hover:bg-primary/20 [&_a]:rounded [&_a]:px-1 [&_a]:align-super [&_a]:text-[10px] [&_a]:font-semibold [&_a]:no-underline [&_hr]:my-3">
            {linkCitations(m.content, m.id, new Set(m.citations.map((c) => c.id)))}
          </Markdown>
        </div>
        {notes.map((n) => (
          <p key={n} className="text-muted-foreground mt-2 flex items-center gap-1.5 text-xs">
            <ShieldCheck className="size-3.5" aria-hidden /> {n}
          </p>
        ))}
        <Sources citations={m.citations} messageId={m.id} />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {m.actions.map((a) => (
            <Button key={a.label} size="sm" variant="outline" onClick={() => onAction?.(a)}>
              <Target /> {a.label}
            </Button>
          ))}
          {m.source !== "safety" && (
            <span className="ml-auto flex items-center gap-1">
              <span className="text-muted-foreground text-xs">Helpful?</span>
              <Button
                size="icon"
                variant="ghost"
                className={cn("size-7", helpful === true && "text-success")}
                aria-label="Helpful"
                aria-pressed={helpful === true}
                onClick={() => rate.mutate(helpful === true ? null : true)}
              >
                <ThumbsUp />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                className={cn("size-7", helpful === false && "text-destructive")}
                aria-label="Not helpful"
                aria-pressed={helpful === false}
                onClick={() => rate.mutate(helpful === false ? null : false)}
              >
                <ThumbsDown />
              </Button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export function Thinking() {
  return (
    <div className="flex justify-start" role="status" aria-live="polite">
      <div className="bg-card text-muted-foreground flex items-center gap-2 rounded-2xl rounded-bl-sm border px-4 py-3 text-sm">
        <span className="flex gap-1" aria-hidden>
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="bg-muted-foreground/60 size-1.5 animate-bounce rounded-full"
              style={{ animationDelay: `${i * 120}ms` }}
            />
          ))}
        </span>
        Tutor is thinking…
      </div>
    </div>
  );
}

export function Composer({
  onSend,
  pending,
  placeholder,
  autoFocus,
}: {
  onSend: (text: string) => void;
  pending: boolean;
  placeholder: string;
  autoFocus?: boolean;
}) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  const send = () => {
    const t = text.trim();
    if (!t || pending) return;
    onSend(t);
    setText("");
  };
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [text]);
  return (
    <form
      className="bg-card focus-within:ring-ring flex items-end gap-2 rounded-xl border p-2 focus-within:ring-2"
      onSubmit={(e) => {
        e.preventDefault();
        send();
      }}
    >
      <label htmlFor="tutor-message" className="sr-only">
        Message the tutor
      </label>
      <textarea
        id="tutor-message"
        ref={ref}
        rows={1}
        maxLength={2000}
        autoFocus={autoFocus}
        value={text}
        placeholder={placeholder}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            send();
          }
        }}
        className="max-h-44 min-h-9 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm outline-none"
      />
      <Button type="submit" size="icon" variant="gradient" aria-label="Send" loading={pending} disabled={!text.trim()}>
        <SendHorizontal />
      </Button>
    </form>
  );
}

const UNAVAILABLE: Record<NonNullable<TutorStatus["reason"]>, string> = {
  not_configured: "The AI tutor isn't switched on yet.",
  disabled: "The AI tutor is turned off right now.",
  daily_limit: "You've used today's AI tutor messages — they reset at midnight.",
  budget: "The AI tutor is paused for today.",
};

export function StatusNote({ status }: { status?: TutorStatus }) {
  if (!status) return null;
  if (!status.ai_available && status.reason) {
    return (
      <Alert variant="info">
        <BookOpen />
        <span>
          {UNAVAILABLE[status.reason]} Until then you&apos;ll get answers from approved study notes, hints and worked
          solutions.
        </span>
      </Alert>
    );
  }
  return (
    <p className="text-muted-foreground text-xs">
      {status.messages_today} of {status.daily_limit} AI messages used today · The tutor never changes your marks or
      mastery.
    </p>
  );
}

/** Message list + sending for one conversation. Shared by the tutor page and the practice panel. */
export function useTutorChat(initial?: { conversationId?: string; messages?: TutorMessage[] }) {
  const qc = useQueryClient();
  const [conversationId, setConversationId] = useState<string | undefined>(initial?.conversationId);
  const [messages, setMessages] = useState<TutorMessage[]>(initial?.messages ?? []);
  const [pendingText, setPendingText] = useState<string | null>(null);

  const reset = useCallback((next?: { conversationId?: string; messages?: TutorMessage[] }) => {
    setConversationId(next?.conversationId);
    setMessages(next?.messages ?? []);
  }, []);

  const send = useMutation({
    mutationFn: (fn: (conversationId?: string) => Promise<TutorReply>) => fn(conversationId),
    onSuccess: (r) => {
      setConversationId(r.conversation.id);
      setMessages((ms) => [...ms, r.student_message, r.reply]);
      void qc.invalidateQueries({ queryKey: ["tutor", "conversations"] });
      void qc.invalidateQueries({ queryKey: ["tutor", "status"] });
    },
    onError: (e) => toast.error(errMsg(e)),
    onSettled: () => setPendingText(null),
  });

  const ask = useCallback(
    (fn: (conversationId?: string) => Promise<TutorReply>, preview: string) => {
      setPendingText(preview);
      send.mutate(fn);
    },
    [send],
  );

  return { conversationId, messages, ask, pending: send.isPending, pendingText, reset };
}

export function PendingBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end opacity-70">
      <div className="bg-primary/10 max-w-[85%] rounded-2xl rounded-br-sm px-4 py-2.5 text-sm whitespace-pre-wrap">
        {text}
      </div>
    </div>
  );
}
