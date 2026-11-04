"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, ArrowLeft, CheckCircle2, Eye, Plus, RotateCcw, Send, Trash2, XCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { QuestionView, TYPE_LABEL } from "@/components/questions/question-view";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { formatDateTime } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import type { CorrectAnswer, Option, QuestionContent, QuestionType, Response } from "@/types/learning";
import { contentApi, type QuestionDetail, type QuestionInput } from "./content-api";
import { STATUS_BADGE } from "./question-list";

const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong.");
const CHOICE_TYPES: QuestionType[] = ["mcq_single", "mcq_multi", "diagram", "assertion_reason"];
const letters = "abcdefghij";

function blank(type: QuestionType): Pick<QuestionInput, "content" | "answer"> {
  switch (type) {
    case "mcq_single":
    case "diagram":
      return {
        content: {
          options: ["", "", "", ""].map((t, i) => ({ id: letters[i], text: t })),
          ...(type === "diagram" ? { image: "", image_alt: "" } : {}),
        },
        answer: { correct: "a" },
      };
    case "mcq_multi":
      return {
        content: { options: ["", "", "", ""].map((t, i) => ({ id: letters[i], text: t })) },
        answer: { correct: [], partial: false },
      };
    case "assertion_reason":
      return { content: { assertion: "", reason: "" }, answer: { correct: "a" } };
    case "numerical":
      return { content: { unit: "" }, answer: { value: 0, tolerance: 0.01 } };
    case "integer":
      return { content: {}, answer: { value: 0 } };
    case "fill_blank":
      return { content: { blanks: 1 }, answer: { accepted: [[""]] } };
    case "match":
      return {
        content: {
          left: [1, 2, 3].map((i) => ({ id: `l${i}`, text: "" })),
          right: [1, 2, 3].map((i) => ({ id: `r${i}`, text: "" })),
        },
        answer: { pairs: { l1: "r1", l2: "r2", l3: "r3" } },
      };
    case "subjective":
      return { content: {}, answer: { model_answer: "" } };
  }
}

const EMPTY: QuestionInput = {
  type: "mcq_single",
  difficulty: 2,
  stem: "",
  ...blank("mcq_single"),
  solution: "",
  hints: [],
  estimated_seconds: 90,
  source: null,
  concepts: [],
};

function fromDetail(d: QuestionDetail): QuestionInput {
  const v = d.latest;
  return {
    type: v.type,
    difficulty: v.difficulty,
    stem: v.stem,
    content: v.content,
    answer: v.answer,
    solution: v.solution,
    hints: v.hints,
    estimated_seconds: v.estimated_seconds,
    source: v.source,
    concepts: d.concepts.map((c) => ({ concept_id: c.id, weight: c.weight })),
  };
}

/** The response that the answer key would produce — used to preview what a correct answer looks like. */
function previewResponse(f: QuestionInput): Response {
  const a = f.answer;
  if (CHOICE_TYPES.includes(f.type)) return { selected: a.correct };
  if (f.type === "numerical" || f.type === "integer") return { value: String(a.value ?? "") };
  if (f.type === "fill_blank") return { values: (a.accepted ?? []).map((x) => x[0] ?? "") };
  if (f.type === "match") return { pairs: a.pairs ?? {} };
  return { text: "" };
}

const AR_OPTIONS: Option[] = [
  { id: "a", text: "Both A and R are true, and R is the correct explanation of A." },
  { id: "b", text: "Both A and R are true, but R is not the correct explanation of A." },
  { id: "c", text: "A is true, but R is false." },
  { id: "d", text: "A is false, but R is true." },
];

function previewContent(f: QuestionInput): QuestionContent {
  return f.type === "assertion_reason" ? { ...f.content, options: AR_OPTIONS } : f.content;
}

function previewReveal(f: QuestionInput): CorrectAnswer {
  const a = f.answer;
  switch (f.type) {
    case "subjective":
      return { model_answer: a.model_answer };
    case "numerical":
    case "integer":
      return { value: a.value, unit: f.content.unit };
    case "fill_blank":
      return { accepted: (a.accepted ?? []).map((x) => x[0]) };
    case "match":
      return { pairs: a.pairs };
    default:
      return { correct: a.correct };
  }
}

function OptionsEditor({ form, set }: { form: QuestionInput; set: (f: Partial<QuestionInput>) => void }) {
  const opts = form.content.options ?? [];
  const multi = form.type === "mcq_multi";
  const correct = form.answer.correct;
  const isRight = (id: string) => (Array.isArray(correct) ? correct.includes(id) : correct === id);
  const setOpts = (o: Option[]) => set({ content: { ...form.content, options: o } });
  const toggle = (id: string) => {
    if (!multi) return set({ answer: { ...form.answer, correct: id } });
    const cur = new Set((correct as string[]) ?? []);
    if (cur.has(id)) cur.delete(id);
    else cur.add(id);
    set({ answer: { ...form.answer, correct: letters.split("").filter((l) => cur.has(l)) } });
  };
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium">Options — tick the correct {multi ? "ones" : "one"}</p>
      {opts.map((o, i) => (
        <div key={o.id} className="flex items-center gap-2">
          <input
            type={multi ? "checkbox" : "radio"}
            name="correct"
            checked={isRight(o.id)}
            onChange={() => toggle(o.id)}
            aria-label={`Option ${o.id.toUpperCase()} is correct`}
            className="accent-primary size-4"
          />
          <span className="text-muted-foreground w-4 text-sm font-semibold">{o.id.toUpperCase()}</span>
          <Input
            value={o.text}
            onChange={(e) => setOpts(opts.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)))}
            placeholder="Option text (supports $maths$)"
            aria-label={`Option ${o.id.toUpperCase()}`}
          />
          {opts.length > 2 && (
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Remove option ${o.id.toUpperCase()}`}
              onClick={() => {
                const next = opts.filter((_, j) => j !== i).map((x, j) => ({ ...x, id: letters[j] }));
                const remap = (id: string) => {
                  const k = opts.findIndex((x) => x.id === id);
                  return k === i ? null : letters[k > i ? k - 1 : k];
                };
                const ans = Array.isArray(correct)
                  ? (correct.map(remap).filter(Boolean) as string[])
                  : (remap(correct as string) ?? "a");
                set({ content: { ...form.content, options: next }, answer: { ...form.answer, correct: ans } });
              }}
            >
              <Trash2 />
            </Button>
          )}
        </div>
      ))}
      {opts.length < 8 && (
        <Button variant="outline" size="sm" onClick={() => setOpts([...opts, { id: letters[opts.length], text: "" }])}>
          <Plus /> Add option
        </Button>
      )}
      {multi && (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="accent-primary size-4"
            checked={!!form.answer.partial}
            onChange={(e) => set({ answer: { ...form.answer, partial: e.target.checked } })}
          />
          Give partial credit when some (but not all) correct options are chosen and none are wrong
        </label>
      )}
    </div>
  );
}

function AnswerEditor({ form, set }: { form: QuestionInput; set: (f: Partial<QuestionInput>) => void }) {
  const c = form.content;
  const a = form.answer;
  switch (form.type) {
    case "mcq_single":
    case "mcq_multi":
      return <OptionsEditor form={form} set={set} />;
    case "diagram":
      return (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField id="image" label="Diagram image URL" hint="Upload to R2 and paste the public URL.">
              <Input value={c.image ?? ""} onChange={(e) => set({ content: { ...c, image: e.target.value } })} />
            </FormField>
            <FormField id="image_alt" label="Image description" hint="Read aloud by screen readers.">
              <Input
                value={c.image_alt ?? ""}
                onChange={(e) => set({ content: { ...c, image_alt: e.target.value } })}
              />
            </FormField>
          </div>
          <OptionsEditor form={form} set={set} />
        </div>
      );
    case "assertion_reason":
      return (
        <div className="space-y-3">
          <FormField id="assertion" label="Assertion (A)">
            <Input value={c.assertion ?? ""} onChange={(e) => set({ content: { ...c, assertion: e.target.value } })} />
          </FormField>
          <FormField id="reason" label="Reason (R)">
            <Input value={c.reason ?? ""} onChange={(e) => set({ content: { ...c, reason: e.target.value } })} />
          </FormField>
          <FormField
            id="ar_correct"
            label="Correct option"
            hint="The four standard assertion–reason options are added automatically."
          >
            <Select value={(a.correct as string) ?? "a"} onChange={(e) => set({ answer: { correct: e.target.value } })}>
              <option value="a">A — Both true, R explains A</option>
              <option value="b">B — Both true, R doesn&apos;t explain A</option>
              <option value="c">C — A true, R false</option>
              <option value="d">D — A false, R true</option>
            </Select>
          </FormField>
        </div>
      );
    case "numerical":
      return (
        <div className="grid gap-3 sm:grid-cols-3">
          <FormField id="value" label="Correct value">
            <Input
              type="number"
              step="any"
              value={a.value ?? ""}
              onChange={(e) => set({ answer: { ...a, value: Number(e.target.value) } })}
            />
          </FormField>
          <FormField id="tolerance" label="Tolerance (±)" hint="Absolute. Blank = 1% of the value.">
            <Input
              type="number"
              step="any"
              min={0}
              value={a.tolerance ?? ""}
              onChange={(e) => {
                const { tolerance: _drop, ...rest } = a; // eslint-disable-line @typescript-eslint/no-unused-vars
                set({ answer: e.target.value === "" ? rest : { ...a, tolerance: Number(e.target.value) } });
              }}
            />
          </FormField>
          <FormField id="unit" label="Unit">
            <Input
              value={c.unit ?? ""}
              onChange={(e) => set({ content: { ...c, unit: e.target.value } })}
              placeholder="e.g. m/s²"
            />
          </FormField>
        </div>
      );
    case "integer":
      return (
        <FormField id="int" label="Correct whole number" className="max-w-xs">
          <Input
            type="number"
            step={1}
            value={a.value ?? ""}
            onChange={(e) => set({ answer: { value: Math.trunc(Number(e.target.value)) } })}
          />
        </FormField>
      );
    case "fill_blank": {
      const acc = a.accepted ?? [];
      return (
        <div className="space-y-3">
          <p className="text-muted-foreground text-sm">
            Mark each blank in the question text with ___ (three underscores).
          </p>
          {acc.map((list, i) => (
            <FormField
              key={i}
              id={`blank-${i}`}
              label={`Blank ${i + 1} — accepted answers`}
              hint="Separate alternatives with commas. Not case-sensitive."
            >
              <Input
                value={list.join(", ")}
                onChange={(e) => {
                  const next = [...acc];
                  next[i] = e.target.value.split(",").map((x) => x.trim());
                  set({ answer: { accepted: next } });
                }}
              />
            </FormField>
          ))}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => set({ content: { ...c, blanks: acc.length + 1 }, answer: { accepted: [...acc, [""]] } })}
            >
              <Plus /> Add blank
            </Button>
            {acc.length > 1 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  set({ content: { ...c, blanks: acc.length - 1 }, answer: { accepted: acc.slice(0, -1) } })
                }
              >
                Remove last
              </Button>
            )}
          </div>
        </div>
      );
    }
    case "match": {
      const left = c.left ?? [];
      const right = c.right ?? [];
      const pairs = a.pairs ?? {};
      return (
        <div className="space-y-3">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <p className="text-sm font-medium">Left column → its match</p>
              {left.map((l, i) => (
                <div key={l.id} className="flex gap-2">
                  <Input
                    value={l.text}
                    aria-label={`Left item ${i + 1}`}
                    onChange={(e) =>
                      set({
                        content: { ...c, left: left.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)) },
                      })
                    }
                  />
                  <Select
                    value={pairs[l.id] ?? ""}
                    aria-label={`Match for left item ${i + 1}`}
                    onChange={(e) => set({ answer: { pairs: { ...pairs, [l.id]: e.target.value } } })}
                  >
                    {right.map((r, k) => (
                      <option key={r.id} value={r.id}>
                        {k + 1}
                      </option>
                    ))}
                  </Select>
                </div>
              ))}
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Right column</p>
              {right.map((r, i) => (
                <div key={r.id} className="flex items-center gap-2">
                  <span className="text-muted-foreground w-4 text-sm">{i + 1}</span>
                  <Input
                    value={r.text}
                    aria-label={`Right item ${i + 1}`}
                    onChange={(e) =>
                      set({
                        content: { ...c, right: right.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)) },
                      })
                    }
                  />
                </div>
              ))}
            </div>
          </div>
          {left.length < 8 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const n = left.length + 1;
                set({
                  content: {
                    ...c,
                    left: [...left, { id: `l${n}`, text: "" }],
                    right: [...right, { id: `r${n}`, text: "" }],
                  },
                  answer: { pairs: { ...pairs, [`l${n}`]: `r${n}` } },
                });
              }}
            >
              <Plus /> Add pair
            </Button>
          )}
        </div>
      );
    }
    case "subjective":
      return (
        <FormField
          id="model"
          label="Model answer"
          hint="Shown to students after they submit. Written answers aren't auto-marked."
        >
          <textarea
            rows={4}
            className="border-input bg-card w-full rounded-lg border p-3 text-sm"
            value={a.model_answer ?? ""}
            onChange={(e) => set({ answer: { model_answer: e.target.value } })}
          />
        </FormField>
      );
  }
}

function ConceptPicker({ form, set }: { form: QuestionInput; set: (f: Partial<QuestionInput>) => void }) {
  const curricula = useQuery({ queryKey: ["admin", "curricula"], queryFn: contentApi.curricula });
  const [cid, setCid] = useState<number | null>(null);
  const curriculumId = cid ?? curricula.data?.[0]?.id ?? null;
  const tree = useQuery({
    queryKey: ["admin", "tree", curriculumId],
    queryFn: () => contentApi.tree(curriculumId!),
    enabled: curriculumId != null,
  });
  const tagged = new Map(form.concepts.map((c) => [c.concept_id, c.weight]));
  const toggle = (id: number) =>
    set({
      concepts: tagged.has(id)
        ? form.concepts.filter((c) => c.concept_id !== id)
        : [...form.concepts, { concept_id: id, weight: 1 }],
    });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Concepts</CardTitle>
        <CardDescription>What this question tests. Weight below 1 means a secondary concept.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {(curricula.data?.length ?? 0) > 1 && (
          <Select value={curriculumId ?? ""} onChange={(e) => setCid(Number(e.target.value))} aria-label="Curriculum">
            {curricula.data!.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        )}
        {tree.isLoading || curricula.isLoading ? (
          <LoadingState className="py-4" />
        ) : (
          <div className="max-h-80 space-y-3 overflow-y-auto pr-1">
            {tree.data?.subjects.flatMap((s) =>
              s.chapters.map((ch) => (
                <div key={ch.id}>
                  <p className="text-muted-foreground mb-1 text-xs font-medium">
                    {s.name} · {ch.name}
                  </p>
                  {ch.topics.flatMap((t) =>
                    t.concepts.map((c) => (
                      <div key={c.id} className="flex items-center gap-2 py-1">
                        <label className="flex flex-1 items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            className="accent-primary size-4"
                            checked={tagged.has(c.id)}
                            onChange={() => toggle(c.id)}
                          />
                          {c.name}
                        </label>
                        {tagged.has(c.id) && (
                          <Select
                            className="h-8 w-20 text-xs"
                            value={String(tagged.get(c.id))}
                            aria-label={`Weight for ${c.name}`}
                            onChange={(e) =>
                              set({
                                concepts: form.concepts.map((x) =>
                                  x.concept_id === c.id ? { ...x, weight: Number(e.target.value) } : x,
                                ),
                              })
                            }
                          >
                            {[1, 0.75, 0.5, 0.25].map((w) => (
                              <option key={w} value={w}>
                                ×{w}
                              </option>
                            ))}
                          </Select>
                        )}
                      </div>
                    )),
                  )}
                </div>
              )),
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function QuestionEditor({ id }: { id?: string }) {
  const router = useRouter();
  const qc = useQueryClient();
  const perms = useAuthStore((s) => s.user?.permissions ?? []);
  const canApprove = perms.includes("questions.approve");
  const detail = useQuery({
    queryKey: ["admin", "question", id],
    queryFn: () => contentApi.question(id!),
    enabled: !!id,
  });
  const [draft, setDraft] = useState<QuestionInput | null>(null);
  const [note, setNote] = useState("");

  const loaded = useMemo(() => (detail.data ? fromDetail(detail.data) : null), [detail.data]);
  const form = draft ?? loaded ?? EMPTY;
  const dirty = draft !== null;
  const set = (patch: Partial<QuestionInput>) => setDraft({ ...form, ...patch });

  const onSaved = (d: QuestionDetail, msg: string) => {
    qc.setQueryData(["admin", "question", d.id], d);
    void qc.invalidateQueries({ queryKey: ["admin", "questions"] });
    void qc.invalidateQueries({ queryKey: ["admin", "qstats"] });
    setDraft(null);
    toast.success(msg);
    if (!id) router.replace(`/admin/questions/${d.id}`);
  };
  const save = useMutation({
    mutationFn: () => (id ? contentApi.save(id, form) : contentApi.create(form)),
    onSuccess: (d) =>
      onSaved(
        d,
        d.published_version_id && d.latest.status === "draft"
          ? "Saved as a new draft — the published version stays live until this is approved."
          : "Saved",
      ),
    onError: (e) => toast.error(errMsg(e)),
  });
  const act = useMutation({
    mutationFn: (a: "submit" | "publish" | "reject" | "archive" | "restore") =>
      contentApi.action(id!, a, note || undefined),
    onSuccess: (d, a) => {
      setNote("");
      onSaved(
        d,
        {
          submit: "Sent for review",
          publish: "Published — students can now get this question",
          reject: "Sent back with your note",
          archive: "Archived",
          restore: "Restored",
        }[a],
      );
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  if (id && detail.isLoading) return <LoadingState />;
  if (id && (detail.isError || !detail.data))
    return <ErrorState message={errMsg(detail.error)} onRetry={() => void detail.refetch()} />;
  const d = detail.data;
  const latestStatus = d?.latest.status;

  return (
    <>
      <Link
        href="/admin/questions"
        className="text-muted-foreground hover:text-foreground mb-4 inline-flex items-center gap-1.5 text-sm"
      >
        <ArrowLeft className="size-4" /> Question bank
      </Link>
      <PageHeader
        title={id ? `Question v${d!.latest.version}` : "New question"}
        description={
          d ? (
            <span className="inline-flex flex-wrap items-center gap-2">
              <Badge variant={STATUS_BADGE[d.status].variant}>{STATUS_BADGE[d.status].label}</Badge>
              {d.published_version_id && latestStatus !== "published" && (
                <Badge variant="blue">An earlier version is live</Badge>
              )}
              {d.is_sample && <Badge variant="outline">Sample</Badge>}
              <span>
                {d.attempts} attempts{d.correct_rate != null && ` · ${Math.round(d.correct_rate * 100)}% correct`}
              </span>
            </span>
          ) : (
            "Saved as a draft. Students only see a question after it's published."
          )
        }
        actions={
          <Button variant="gradient" disabled={!dirty && !!id} loading={save.isPending} onClick={() => save.mutate()}>
            {id ? "Save changes" : "Create draft"}
          </Button>
        }
      />
      {d?.latest.review_note && latestStatus === "rejected" && (
        <Alert variant="destructive" className="mb-4">
          <XCircle />
          <p>
            <strong>Changes requested:</strong> {d.latest.review_note}
          </p>
        </Alert>
      )}

      <div className="grid gap-4 xl:grid-cols-[1fr_24rem]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Question</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <FormField id="type" label="Type">
                  <Select
                    value={form.type}
                    disabled={!!id}
                    onChange={(e) => {
                      const t = e.target.value as QuestionType;
                      set({ type: t, ...blank(t) });
                    }}
                  >
                    {Object.entries(TYPE_LABEL).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v}
                      </option>
                    ))}
                  </Select>
                </FormField>
                <FormField id="difficulty" label="Difficulty" hint="1 recall · 5 olympiad">
                  <Select value={form.difficulty} onChange={(e) => set({ difficulty: Number(e.target.value) })}>
                    {[1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </Select>
                </FormField>
                <FormField id="est" label="Expected time (s)">
                  <Input
                    type="number"
                    min={10}
                    max={3600}
                    value={form.estimated_seconds}
                    onChange={(e) => set({ estimated_seconds: Number(e.target.value) })}
                  />
                </FormField>
              </div>
              <FormField id="stem" label="Question text" hint="Markdown, with $inline$ and $$display$$ maths.">
                <textarea
                  rows={4}
                  className="border-input bg-card w-full rounded-lg border p-3 font-mono text-sm"
                  value={form.stem}
                  onChange={(e) => set({ stem: e.target.value })}
                />
              </FormField>
              <AnswerEditor form={form} set={set} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Solution & hints</CardTitle>
              <CardDescription>
                The solution is shown after the student answers. Hints are revealed one at a time.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField id="solution" label="Worked solution">
                <textarea
                  rows={4}
                  className="border-input bg-card w-full rounded-lg border p-3 font-mono text-sm"
                  value={form.solution}
                  onChange={(e) => set({ solution: e.target.value })}
                />
              </FormField>
              {form.hints.map((h, i) => (
                <div key={i} className="flex gap-2">
                  <Input
                    value={h}
                    aria-label={`Hint ${i + 1}`}
                    onChange={(e) => set({ hints: form.hints.map((x, j) => (j === i ? e.target.value : x)) })}
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Remove hint ${i + 1}`}
                    onClick={() => set({ hints: form.hints.filter((_, j) => j !== i) })}
                  >
                    <Trash2 />
                  </Button>
                </div>
              ))}
              {form.hints.length < 5 && (
                <Button variant="outline" size="sm" onClick={() => set({ hints: [...form.hints, ""] })}>
                  <Plus /> Add hint
                </Button>
              )}
              <FormField
                id="source"
                label="Source"
                hint="Where this question came from, for licensing and attribution."
              >
                <Input value={form.source ?? ""} onChange={(e) => set({ source: e.target.value || null })} />
              </FormField>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <ConceptPicker form={form} set={set} />

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="size-4" /> Student preview
              </CardTitle>
              <CardDescription>With the answer key applied, as shown after answering.</CardDescription>
            </CardHeader>
            <CardContent>
              {form.stem ? (
                <QuestionView
                  idPrefix="preview"
                  type={form.type}
                  stem={form.stem}
                  content={previewContent(form)}
                  response={previewResponse(form)}
                  reveal={previewReveal(form)}
                />
              ) : (
                <p className="text-muted-foreground text-sm">Write the question text to see a preview.</p>
              )}
            </CardContent>
          </Card>

          {d && (
            <Card>
              <CardHeader>
                <CardTitle>Review & publishing</CardTitle>
                <CardDescription>Draft → review → approval → publication.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {dirty && <p className="text-warning text-xs">Save your changes first.</p>}
                <div className="flex flex-wrap gap-2">
                  {(latestStatus === "draft" || latestStatus === "rejected") && (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={dirty}
                      loading={act.isPending && act.variables === "submit"}
                      onClick={() => act.mutate("submit")}
                    >
                      <Send /> Submit for review
                    </Button>
                  )}
                  {canApprove && (latestStatus === "draft" || latestStatus === "in_review") && !d.archived_at && (
                    <Button
                      size="sm"
                      variant="gradient"
                      disabled={dirty}
                      loading={act.isPending && act.variables === "publish"}
                      onClick={() => act.mutate("publish")}
                    >
                      <CheckCircle2 /> Approve & publish
                    </Button>
                  )}
                  {canApprove && latestStatus === "in_review" && (
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button size="sm" variant="outline" disabled={dirty}>
                          <XCircle /> Request changes
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Request changes</DialogTitle>
                          <DialogDescription>The author sees this note on the question.</DialogDescription>
                        </DialogHeader>
                        <Input
                          value={note}
                          onChange={(e) => setNote(e.target.value)}
                          placeholder="What needs fixing?"
                          aria-label="Review note"
                        />
                        <DialogFooter>
                          <DialogClose asChild>
                            <Button variant="outline">Cancel</Button>
                          </DialogClose>
                          <DialogClose asChild>
                            <Button
                              variant="destructive"
                              disabled={note.trim().length < 3}
                              onClick={() => act.mutate("reject")}
                            >
                              Send back
                            </Button>
                          </DialogClose>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                  )}
                  {d.archived_at ? (
                    <Button
                      size="sm"
                      variant="outline"
                      loading={act.isPending && act.variables === "restore"}
                      onClick={() => act.mutate("restore")}
                    >
                      <RotateCcw /> Restore
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-destructive"
                      loading={act.isPending && act.variables === "archive"}
                      onClick={() => act.mutate("archive")}
                    >
                      <Archive /> Archive
                    </Button>
                  )}
                </div>
                <div>
                  <p className="text-muted-foreground mb-1 text-xs font-medium tracking-wide uppercase">Versions</p>
                  <ul className="divide-y text-sm">
                    {d.versions.map((v) => (
                      <li key={v.id} className="flex items-center justify-between gap-2 py-1.5">
                        <span>v{v.version}</span>
                        <span className="text-muted-foreground text-xs">
                          {formatDateTime(v.published_at ?? v.created_at)}
                        </span>
                        <Badge
                          variant={
                            v.status === "published" ? "success" : v.status === "superseded" ? "muted" : "outline"
                          }
                        >
                          {v.status}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                  <p className="text-muted-foreground mt-2 text-xs">
                    Past attempts always keep the version that was delivered.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
