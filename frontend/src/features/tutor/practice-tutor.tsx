"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { TutorMode } from "@/types/tutor";
import { tutor } from "./api";
import { Composer, MessageBubble, MODE_META, PendingBubble, StatusNote, Thinking, useTutorChat } from "./chat";

/**
 * The tutor beside a practice question. Before answering it only ever gets the question as
 * the student sees it (never the answer key); help here counts like a hint. After answering
 * it can compare the student's answer with the worked solution.
 */
export function PracticeTutor({
  sessionQuestionId,
  answered,
  wrong,
  conceptId,
  onClose,
  onHintShown,
  onPractise,
}: {
  sessionQuestionId: string;
  answered: boolean;
  wrong: boolean;
  conceptId?: number;
  onClose: () => void;
  onHintShown: () => void;
  onPractise: (conceptId: number) => void;
}) {
  const chat = useTutorChat();
  // The mode the student picked, remembered for the current before/after-answer state.
  const [picked, setPicked] = useState<{ answered: boolean; mode: TutorMode } | null>(null);
  const mode: TutorMode = picked?.answered === answered ? picked.mode : answered ? "mistake" : "hint";
  const setMode = (m: TutorMode) => setPicked({ answered, mode: m });
  const status = useQuery({ queryKey: ["tutor", "status"], queryFn: tutor.status });
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [chat.messages.length, chat.pending]);
  const last = chat.messages.at(-1);
  useEffect(() => {
    if (last?.flags.includes("hint_revealed")) onHintShown();
  }, [last, onHintShown]);

  const quick: { mode: TutorMode; label: string; run: () => void }[] = answered
    ? [
        {
          mode: "mistake",
          label: wrong ? "Find my mistake" : "Explain this question",
          run: () => chat.ask((c) => tutor.explain(sessionQuestionId, c), MODE_META.mistake.label),
        },
        {
          mode: "teach",
          label: "Teach me the concept",
          run: () =>
            chat.ask(
              (c) =>
                tutor.ask({
                  mode: "teach",
                  message: "Teach me the idea behind this question.",
                  conversation_id: c,
                  session_question_id: sessionQuestionId,
                }),
              "Teach me the idea behind this question.",
            ),
        },
      ]
    : [
        {
          mode: "hint",
          label: "Give a hint",
          run: () => chat.ask((c) => tutor.hint(sessionQuestionId, c), "Can I have a hint?"),
        },
        {
          mode: "solve",
          label: "Solve with me",
          run: () =>
            chat.ask(
              (c) =>
                tutor.ask({
                  mode: "solve",
                  message: "Let's solve this together, one step at a time.",
                  conversation_id: c,
                  session_question_id: sessionQuestionId,
                }),
              "Let's solve this together, one step at a time.",
            ),
        },
        {
          mode: "teach",
          label: "Teach me the concept",
          run: () =>
            chat.ask(
              (c) =>
                tutor.ask({
                  mode: "teach",
                  message: "Explain the concept this question is about — without solving it.",
                  conversation_id: c,
                  session_question_id: sessionQuestionId,
                }),
              "Explain the concept this question is about — without solving it.",
            ),
        },
      ];

  return (
    <Card className="mt-4">
      <CardContent className="space-y-3 p-4">
        <div className="flex items-center gap-2">
          <Bot className="text-primary size-5" aria-hidden />
          <p className="flex-1 font-semibold">Ask the tutor</p>
          <Button size="icon" variant="ghost" className="size-8" aria-label="Close tutor" onClick={onClose}>
            <X />
          </Button>
        </div>
        <StatusNote status={status.data} />
        <div className="flex flex-wrap gap-2">
          {quick.map((q) => {
            const Icon = MODE_META[q.mode].icon;
            return (
              <Button
                key={q.label}
                size="sm"
                variant={mode === q.mode ? "secondary" : "outline"}
                disabled={chat.pending}
                onClick={() => {
                  setMode(q.mode);
                  q.run();
                }}
              >
                <Icon /> {q.label}
              </Button>
            );
          })}
        </div>
        {!answered && (
          <p className="text-muted-foreground text-xs">
            Help on a question you haven&apos;t answered yet counts like a hint, so your mastery estimate stays honest.
          </p>
        )}
        {(chat.messages.length > 0 || chat.pendingText) && (
          <div className="max-h-[28rem] space-y-3 overflow-y-auto pr-1">
            {chat.messages.map((m) => (
              <MessageBubble key={m.id} m={m} onAction={(a) => onPractise(a.concept_id)} />
            ))}
            {chat.pendingText && <PendingBubble text={chat.pendingText} />}
            {chat.pending && <Thinking />}
            <div ref={end} />
          </div>
        )}
        {chat.conversationId && (
          <Composer
            pending={chat.pending}
            placeholder={MODE_META[mode].placeholder}
            onSend={(text) =>
              chat.ask(
                (c) =>
                  tutor.ask({
                    mode,
                    message: text,
                    conversation_id: c,
                    session_question_id: sessionQuestionId,
                    concept_id: conceptId,
                  }),
                text,
              )
            }
          />
        )}
      </CardContent>
    </Card>
  );
}
