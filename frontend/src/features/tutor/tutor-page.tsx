"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, MessageSquarePlus, Trash2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { learning } from "@/features/learning/api";
import { useStartSession } from "@/features/learning/use-start-session";
import { cn, formatRelative } from "@/lib/utils";
import type { ConversationDetail, TutorMode } from "@/types/tutor";
import { tutor } from "./api";
import {
  Composer,
  errMsg,
  MessageBubble,
  MODE_META,
  MODES,
  ModePicker,
  PendingBubble,
  StatusNote,
  Thinking,
  useTutorChat,
} from "./chat";

const STARTERS: Record<TutorMode, string[]> = {
  teach: ["Explain this concept simply", "Why does this work?", "Give me a real-life example"],
  hint: ["I'm stuck on the first step", "Which formula should I use?"],
  solve: ["Help me solve a problem step by step", "Check my first step"],
  test: ["Test me", "Give me a harder question"],
  mistake: ["Here's my working — where did I go wrong?", "Why is my answer wrong?"],
};

/** One conversation. Remounted (via `key`) whenever a different conversation is opened. */
function ChatPane({
  initial,
  initialMode,
  initialConcept,
  onCreated,
}: {
  initial?: ConversationDetail;
  initialMode: TutorMode;
  initialConcept?: number;
  onCreated: (id: string) => void;
}) {
  const startSession = useStartSession();
  const [mode, setMode] = useState<TutorMode>(initial?.messages.at(-1)?.mode ?? initial?.mode ?? initialMode);
  const [conceptId, setConceptId] = useState<number | undefined>(initial?.concept?.id ?? initialConcept);
  const chat = useTutorChat({ conversationId: initial?.id, messages: initial?.messages });
  const end = useRef<HTMLDivElement>(null);
  const status = useQuery({ queryKey: ["tutor", "status"], queryFn: tutor.status });
  const tree = useQuery({ queryKey: ["my-curriculum"], queryFn: learning.myCurriculum });

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [chat.messages.length, chat.pending]);
  useEffect(() => {
    if (chat.conversationId && !initial) onCreated(chat.conversationId);
  }, [chat.conversationId, initial, onCreated]);

  const concepts = useMemo(
    () =>
      (tree.data?.subjects ?? []).flatMap((s) =>
        s.chapters.map((ch) => ({
          label: `${s.name} · ${ch.name}`,
          items: ch.topics.flatMap((t) => t.concepts.map((c) => ({ id: c.id, name: c.name }))),
        })),
      ),
    [tree.data],
  );

  function send(text: string) {
    chat.ask((conversation_id) => tutor.ask({ mode, message: text, conversation_id, concept_id: conceptId }), text);
  }

  return (
    <div className="min-w-0 space-y-4">
      <ModePicker value={mode} onChange={setMode} />
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <label htmlFor="tutor-concept" className="text-sm font-medium whitespace-nowrap">
          Concept
        </label>
        <Select
          id="tutor-concept"
          value={conceptId ?? ""}
          onChange={(e) => setConceptId(e.target.value ? Number(e.target.value) : undefined)}
          className="sm:max-w-md"
        >
          <option value="">Any — I&apos;ll describe it</option>
          {concepts.map((g) => (
            <optgroup key={g.label} label={g.label}>
              {g.items.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </optgroup>
          ))}
        </Select>
      </div>
      <StatusNote status={status.data} />

      <Card className="flex min-h-[26rem] flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto p-4" aria-live="polite">
          {!chat.messages.length && !chat.pendingText ? (
            <div className="space-y-4">
              <EmptyState
                icon={Bot}
                title={MODE_META[mode].label}
                description={`${MODE_META[mode].blurb}. Pick a concept above for answers grounded in your syllabus.`}
              />
              <div className="flex flex-wrap justify-center gap-2">
                {STARTERS[mode].map((s) => (
                  <Button key={s} size="sm" variant="secondary" onClick={() => send(s)} disabled={chat.pending}>
                    {s}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            chat.messages.map((m) => (
              <MessageBubble
                key={m.id}
                m={m}
                onAction={(a) => startSession.mutate({ mode: "topic", concept_ids: [a.concept_id] })}
              />
            ))
          )}
          {chat.pendingText && <PendingBubble text={chat.pendingText} />}
          {chat.pending && <Thinking />}
          <div ref={end} />
        </div>
        <div className="border-t p-3">
          <Composer onSend={send} pending={chat.pending} placeholder={MODE_META[mode].placeholder} />
          <p className="text-muted-foreground mt-1.5 px-1 text-[11px]">
            Enter to send · Shift+Enter for a new line · Don&apos;t share personal details.
          </p>
        </div>
      </Card>
    </div>
  );
}

export function TutorPage() {
  const params = useSearchParams();
  const router = useRouter();
  const qc = useQueryClient();
  const modeParam = params.get("mode") as TutorMode | null;
  const initialMode = modeParam && MODES.includes(modeParam) ? modeParam : "teach";
  const initialConcept = params.get("concept") ? Number(params.get("concept")) : undefined;

  // `openId` = a past conversation being viewed; `liveId` = one created in this pane.
  const [openId, setOpenId] = useState<string | undefined>(params.get("c") ?? undefined);
  const [liveId, setLiveId] = useState<string | undefined>();
  const [paneKey, setPaneKey] = useState(0);

  const list = useQuery({ queryKey: ["tutor", "conversations"], queryFn: tutor.conversations });
  const detail = useQuery({
    queryKey: ["tutor", "conversation", openId],
    queryFn: () => tutor.conversation(openId!),
    enabled: !!openId,
    staleTime: Infinity, // the pane owns the live message list once open
  });

  function newChat() {
    setOpenId(undefined);
    setLiveId(undefined);
    setPaneKey((k) => k + 1);
    router.replace("/tutor");
  }

  const remove = useMutation({
    mutationFn: (id: string) => tutor.remove(id),
    onSuccess: (_, id) => {
      void qc.invalidateQueries({ queryKey: ["tutor", "conversations"] });
      qc.removeQueries({ queryKey: ["tutor", "conversation", id] });
      if (id === openId || id === liveId) newChat();
      toast.success("Conversation deleted");
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  const active = openId ?? liveId;

  return (
    <>
      <PageHeader
        title="AI Tutor"
        description="Guides your reasoning instead of handing you answers, using approved study material."
        actions={
          <Button variant="outline" onClick={newChat}>
            <MessageSquarePlus /> New chat
          </Button>
        }
      />
      <div className="grid gap-6 lg:grid-cols-[17rem_1fr]">
        <Card className="order-2 h-fit p-2 lg:order-1">
          <p className="text-muted-foreground px-2 pt-1 pb-2 text-xs font-semibold tracking-wide uppercase">
            Conversations
          </p>
          {list.isLoading ? (
            <LoadingState />
          ) : !list.data?.length ? (
            <p className="text-muted-foreground px-2 pb-2 text-sm">Your chats with the tutor will appear here.</p>
          ) : (
            <ul className="max-h-[28rem] space-y-0.5 overflow-y-auto">
              {list.data.map((c) => (
                <li key={c.id} className="group flex items-center">
                  <button
                    type="button"
                    onClick={() => {
                      if (c.id === active) return;
                      qc.removeQueries({ queryKey: ["tutor", "conversation", c.id] }); // load fresh
                      setOpenId(c.id);
                      setLiveId(undefined);
                      router.replace(`/tutor?c=${c.id}`);
                    }}
                    className={cn(
                      "hover:bg-muted min-w-0 flex-1 rounded-md px-2 py-1.5 text-left",
                      c.id === active && "bg-muted",
                    )}
                    aria-current={c.id === active ? "true" : undefined}
                  >
                    <span className="block truncate text-sm font-medium">{c.title}</span>
                    <span className="text-muted-foreground text-xs">{formatRelative(c.updated_at)}</span>
                  </button>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="size-7 opacity-60 group-hover:opacity-100"
                    aria-label={`Delete “${c.title}”`}
                    onClick={() => remove.mutate(c.id)}
                  >
                    <Trash2 />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="order-1 lg:order-2">
          {openId && detail.isLoading ? (
            <LoadingState />
          ) : openId && (detail.isError || !detail.data) ? (
            <ErrorState message={errMsg(detail.error)} onRetry={() => void detail.refetch()} />
          ) : (
            <ChatPane
              key={openId ?? `new-${paneKey}`}
              initial={openId ? detail.data : undefined}
              initialMode={initialMode}
              initialConcept={initialConcept}
              onCreated={setLiveId}
            />
          )}
        </div>
      </div>
    </>
  );
}
