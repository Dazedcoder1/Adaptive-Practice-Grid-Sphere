"use client";

import { Check, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { CorrectAnswer, Option, QuestionContent, QuestionType, Response } from "@/types/learning";
import { Markdown } from "./markdown";

type Props = {
  type: QuestionType;
  stem: string;
  content: QuestionContent;
  response: Response;
  onChange?: (r: Response) => void;
  /** After answering: lock inputs and mark right/wrong. */
  reveal?: CorrectAnswer | null;
  idPrefix?: string;
};

export const TYPE_LABEL: Record<QuestionType, string> = {
  mcq_single: "Single correct",
  mcq_multi: "Multiple correct",
  numerical: "Numerical",
  integer: "Integer",
  fill_blank: "Fill in the blanks",
  match: "Match the following",
  assertion_reason: "Assertion & reason",
  subjective: "Written answer",
  diagram: "Diagram",
};

/** True once the student has given enough of an answer to submit. */
export function isComplete(type: QuestionType, content: QuestionContent, r: Response) {
  switch (type) {
    case "mcq_multi":
      return Array.isArray(r.selected) && r.selected.length > 0;
    case "numerical":
    case "integer":
      return !!r.value?.trim();
    case "fill_blank":
      return (r.values ?? []).filter((v) => v?.trim()).length === (content.blanks ?? 0);
    case "match":
      return Object.keys(r.pairs ?? {}).length === (content.left?.length ?? 0);
    case "subjective":
      return !!r.text?.trim();
    default:
      return typeof r.selected === "string";
  }
}

function OptionRow({
  option,
  index,
  multi,
  checked,
  disabled,
  state,
  onToggle,
  name,
}: {
  option: Option;
  index: number;
  multi: boolean;
  checked: boolean;
  disabled: boolean;
  state: "correct" | "wrong" | "missed" | null;
  onToggle: () => void;
  name: string;
}) {
  return (
    <label
      className={cn(
        "bg-card flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 transition-colors",
        !disabled && "hover:border-primary/40 hover:bg-primary/5",
        checked && !state && "border-primary bg-primary/5 ring-primary/20 ring-2",
        state === "correct" && "border-success bg-success/5",
        state === "missed" && "border-success bg-success/5 border-dashed",
        state === "wrong" && "border-destructive bg-destructive/5",
        disabled && "cursor-default",
      )}
    >
      <input
        type={multi ? "checkbox" : "radio"}
        name={name}
        className="sr-only"
        checked={checked}
        disabled={disabled}
        onChange={onToggle}
      />
      <span
        className={cn(
          "flex size-6 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
          multi && "rounded-md",
          checked ? "border-primary bg-primary text-white" : "bg-muted text-muted-foreground",
          state === "correct" && "border-success bg-success text-white",
          state === "missed" && "border-success text-success bg-transparent",
          state === "wrong" && "border-destructive bg-destructive text-white",
        )}
        aria-hidden
      >
        {state === "correct" || state === "missed" ? (
          <Check className="size-3.5" />
        ) : state === "wrong" ? (
          <X className="size-3.5" />
        ) : (
          String.fromCharCode(65 + index)
        )}
      </span>
      <Markdown className="flex-1 pt-0.5">{option.text}</Markdown>
    </label>
  );
}

export function QuestionView({ type, stem, content, response, onChange, reveal, idPrefix = "q" }: Props) {
  const locked = !onChange || !!reveal;
  const set = (patch: Response) => onChange?.({ ...response, ...patch });

  const body = (() => {
    switch (type) {
      case "mcq_single":
      case "diagram":
      case "assertion_reason":
      case "mcq_multi": {
        const multi = type === "mcq_multi";
        const selected = multi ? ((response.selected as string[]) ?? []) : (response.selected as string | undefined);
        const correct = reveal?.correct;
        return (
          <div className="space-y-2" role={multi ? "group" : "radiogroup"} aria-label="Options">
            {(content.options ?? []).map((o, i) => {
              const isChecked = multi ? (selected as string[]).includes(o.id) : selected === o.id;
              const isRight = Array.isArray(correct) ? correct.includes(o.id) : correct === o.id;
              const state = !reveal
                ? null
                : isRight && isChecked
                  ? "correct"
                  : isRight
                    ? "missed"
                    : isChecked
                      ? "wrong"
                      : null;
              return (
                <OptionRow
                  key={o.id}
                  option={o}
                  index={i}
                  multi={multi}
                  name={`${idPrefix}-opt`}
                  checked={isChecked}
                  disabled={locked}
                  state={state}
                  onToggle={() => {
                    if (!multi) return set({ selected: o.id });
                    const cur = new Set(selected as string[]);
                    if (cur.has(o.id)) cur.delete(o.id);
                    else cur.add(o.id);
                    set({ selected: [...cur] });
                  }}
                />
              );
            })}
            {multi && !reveal && <p className="text-muted-foreground text-xs">Select all that apply.</p>}
          </div>
        );
      }
      case "numerical":
      case "integer":
        return (
          <div className="space-y-2">
            <label htmlFor={`${idPrefix}-value`} className="text-sm font-medium">
              Your answer
            </label>
            <div className="flex max-w-xs items-center gap-2">
              <Input
                id={`${idPrefix}-value`}
                inputMode={type === "integer" ? "numeric" : "decimal"}
                autoComplete="off"
                value={response.value ?? ""}
                disabled={locked}
                onChange={(e) => set({ value: e.target.value })}
                placeholder={type === "integer" ? "Whole number" : "e.g. 2.5"}
              />
              {content.unit && <span className="text-muted-foreground text-sm">{content.unit}</span>}
            </div>
            {reveal?.value !== undefined && (
              <p className="text-success text-sm">
                Correct answer: <strong>{reveal.value}</strong> {reveal.unit ?? ""}
              </p>
            )}
          </div>
        );
      case "fill_blank": {
        const values = response.values ?? Array(content.blanks ?? 0).fill("");
        return (
          <div className="grid gap-3 sm:grid-cols-2">
            {Array.from({ length: content.blanks ?? 0 }, (_, i) => (
              <div key={i} className="space-y-1.5">
                <label htmlFor={`${idPrefix}-blank-${i}`} className="text-sm font-medium">
                  Blank {i + 1}
                </label>
                <Input
                  id={`${idPrefix}-blank-${i}`}
                  autoComplete="off"
                  value={values[i] ?? ""}
                  disabled={locked}
                  onChange={(e) => {
                    const next = [...values];
                    next[i] = e.target.value;
                    set({ values: next });
                  }}
                />
                {reveal?.accepted && (
                  <p className="text-success text-xs">
                    Answer: <strong>{reveal.accepted[i]}</strong>
                  </p>
                )}
              </div>
            ))}
          </div>
        );
      }
      case "match": {
        const pairs = response.pairs ?? {};
        return (
          <div className="space-y-2">
            {(content.left ?? []).map((l) => {
              const right = reveal?.pairs?.[l.id];
              const ok = reveal ? pairs[l.id] === right : null;
              return (
                <div
                  key={l.id}
                  className={cn(
                    "bg-card grid items-center gap-2 rounded-xl border p-3 sm:grid-cols-[1fr_minmax(0,16rem)]",
                    ok === true && "border-success bg-success/5",
                    ok === false && "border-destructive bg-destructive/5",
                  )}
                >
                  <Markdown>{l.text}</Markdown>
                  <div>
                    <Select
                      aria-label={`Match for ${l.text}`}
                      className="w-full"
                      value={pairs[l.id] ?? ""}
                      disabled={locked}
                      onChange={(e) => set({ pairs: { ...pairs, [l.id]: e.target.value } })}
                    >
                      <option value="" disabled>
                        Choose…
                      </option>
                      {(content.right ?? []).map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.text}
                        </option>
                      ))}
                    </Select>
                    {ok === false && (
                      <p className="text-success mt-1 text-xs">
                        Correct: {(content.right ?? []).find((r) => r.id === right)?.text}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        );
      }
      case "subjective":
        return (
          <div className="space-y-2">
            <label htmlFor={`${idPrefix}-text`} className="text-sm font-medium">
              Your answer
            </label>
            <textarea
              id={`${idPrefix}-text`}
              rows={6}
              maxLength={10000}
              className="border-input bg-card focus-visible:border-ring focus-visible:ring-ring/20 w-full rounded-lg border p-3 text-sm focus-visible:ring-3 focus-visible:outline-none disabled:opacity-60"
              value={response.text ?? ""}
              disabled={locked}
              onChange={(e) => set({ text: e.target.value })}
            />
            {reveal?.model_answer && (
              <div className="bg-muted/60 rounded-lg p-3">
                <p className="mb-1 text-xs font-semibold tracking-wide uppercase">Model answer</p>
                <Markdown>{reveal.model_answer}</Markdown>
              </div>
            )}
          </div>
        );
    }
  })();

  return (
    <div className="space-y-5">
      <Markdown className="text-base">{stem}</Markdown>
      {type === "assertion_reason" && (
        <div className="grid gap-2 sm:grid-cols-2">
          <div className="bg-muted/50 rounded-xl p-3">
            <p className="text-muted-foreground mb-1 text-xs font-semibold">Assertion (A)</p>
            <Markdown>{content.assertion ?? ""}</Markdown>
          </div>
          <div className="bg-muted/50 rounded-xl p-3">
            <p className="text-muted-foreground mb-1 text-xs font-semibold">Reason (R)</p>
            <Markdown>{content.reason ?? ""}</Markdown>
          </div>
        </div>
      )}
      {type === "diagram" && content.image && (
        // eslint-disable-next-line @next/next/no-img-element -- images come from R2/any host
        <img src={content.image} alt={content.image_alt ?? "Diagram"} className="max-h-80 rounded-xl border" />
      )}
      {body}
    </div>
  );
}
