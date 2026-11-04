"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, CircleCheck, CircleDashed, FileStack, KeyRound, Plug, Wallet } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { StatCard } from "@/components/dashboard/stat-card";
import { ErrorState, LoadingState } from "@/components/feedback/states";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/services/api";
import { aiApi, type AiSettings, type ProviderStatus } from "../ai-api";
import { AiHeader } from "./ai-tabs";

const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong.");

function ProviderRow({ title, p, empty }: { title: string; p: ProviderStatus; empty: string }) {
  return (
    <div className="flex items-start gap-3 py-3">
      {p?.ready ? (
        <CircleCheck className="text-success mt-0.5 size-5" aria-hidden />
      ) : (
        <CircleDashed className="text-muted-foreground mt-0.5 size-5" aria-hidden />
      )}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium">{title}</p>
        {p ? (
          <p className="text-muted-foreground text-sm">
            {p.label} · {p.ready ? <code className="text-xs">{p.model}</code> : "API key missing"}
          </p>
        ) : (
          <p className="text-muted-foreground text-sm">{empty}</p>
        )}
      </div>
      <Badge variant={p?.ready ? "success" : "muted"}>{p?.ready ? "Ready" : "Not set up"}</Badge>
    </div>
  );
}

type NumField = { key: keyof AiSettings; label: string; hint?: string; step?: string; min?: number; max?: number };

const GROUPS: { title: string; description: string; fields: NumField[] }[] = [
  {
    title: "Limits",
    description: "When a limit is reached the tutor keeps answering from study notes.",
    fields: [
      { key: "student_daily_messages", label: "AI messages per student per day", min: 0 },
      { key: "student_daily_tokens", label: "Tokens per student per day", min: 0 },
      { key: "platform_daily_cost_usd", label: "Platform cost limit per day (USD)", step: "0.01", min: 0 },
    ],
  },
  {
    title: "Prices (for cost estimates)",
    description: "Enter your provider's current rates in USD per million tokens. Leave 0 if unknown.",
    fields: [
      { key: "input_price_per_mtok", label: "Input", step: "0.0001", min: 0 },
      { key: "output_price_per_mtok", label: "Output", step: "0.0001", min: 0 },
      { key: "embedding_price_per_mtok", label: "Embeddings", step: "0.0001", min: 0 },
    ],
  },
  {
    title: "Generation",
    description: "Replies are checked before students see them, whatever these are set to.",
    fields: [
      { key: "temperature", label: "Temperature", step: "0.05", min: 0, max: 1.5 },
      { key: "max_output_tokens", label: "Max reply tokens", min: 100, max: 8000 },
    ],
  },
  {
    title: "Retrieval & chunking",
    description: "Chunk sizes apply when a document is (re)processed.",
    fields: [
      { key: "retrieval_top_k", label: "Passages sent to the tutor", min: 1, max: 10 },
      { key: "min_similarity", label: "Minimum semantic similarity", step: "0.05", min: 0, max: 1 },
      { key: "chunk_target_tokens", label: "Passage size (tokens)", min: 80, max: 1500 },
      { key: "chunk_overlap_tokens", label: "Overlap (tokens)", min: 0, max: 400 },
    ],
  },
  {
    title: "Privacy",
    description: "Older tutor conversations are deleted automatically.",
    fields: [{ key: "conversation_retention_days", label: "Keep conversations for (days)", min: 7, max: 3650 }],
  },
];

function withoutTimestamp(s: AiSettings & { updated_at: string }): AiSettings {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { updated_at, ...rest } = s;
  return rest;
}

export function AiOverviewPage() {
  const qc = useQueryClient();
  const ov = useQuery({ queryKey: ["admin", "ai", "overview"], queryFn: aiApi.overview });
  const [draft, setForm] = useState<AiSettings | null>(null);
  const form = draft ?? (ov.data ? withoutTimestamp(ov.data.settings) : null);

  const save = useMutation({
    mutationFn: (s: AiSettings) => aiApi.saveSettings(s),
    onSuccess: () => {
      toast.success("AI settings saved");
      void qc.invalidateQueries({ queryKey: ["admin", "ai", "overview"] });
    },
    onError: (e) => toast.error(errMsg(e)),
  });
  const test = useMutation({
    mutationFn: (kind: "chat" | "embedding") => aiApi.test(kind),
    onSuccess: (r) => (r.ok ? toast.success(r.message) : toast.error(r.message)),
    onError: (e) => toast.error(errMsg(e)),
  });

  if (ov.isLoading) return <LoadingState />;
  if (ov.isError || !ov.data || !form)
    return <ErrorState message={errMsg(ov.error)} onRetry={() => void ov.refetch()} />;
  const d = ov.data;
  const docs = d.documents;
  const set = <K extends keyof AiSettings>(k: K, v: AiSettings[K]) => setForm({ ...form, [k]: v });

  return (
    <>
      <AiHeader />
      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Approved documents"
          value={docs.documents.approved}
          icon={FileStack}
          hint={docs.documents.review ? `${docs.documents.review} waiting for review` : "Nothing waiting for review"}
          tone={docs.documents.review ? "warning" : "default"}
        />
        <StatCard
          label="Searchable passages"
          value={docs.approved_passages}
          icon={BookOpen}
          hint={
            d.embeddings?.ready
              ? `${docs.embedded_passages} with semantic vectors`
              : "Keyword search only — no embedding model set up"
          }
        />
        <StatCard
          label="AI cost today"
          value={`$${d.today.cost_usd.toFixed(2)}`}
          icon={Wallet}
          hint={`Daily limit $${d.today.limit_usd.toFixed(2)}${d.settings.input_price_per_mtok ? "" : " · prices not set"}`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <form
          className="space-y-6"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate(form);
          }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Tutor</CardTitle>
              <CardDescription>Turning the AI off keeps the tutor working from approved study notes.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <label className="flex items-center gap-3 text-sm">
                <Checkbox
                  checked={form.tutor_enabled}
                  onCheckedChange={(v) => set("tutor_enabled", v === true)}
                  aria-label="AI tutor enabled"
                />
                AI tutor enabled for students
              </label>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  id="chat_model"
                  label="Model"
                  hint={`Blank = ${d.llm.primary?.model ?? "the provider's default"}`}
                >
                  <Input
                    value={form.chat_model}
                    placeholder={d.llm.primary?.model ?? ""}
                    onChange={(e) => set("chat_model", e.target.value)}
                  />
                </FormField>
                <FormField id="fallback_model" label="Fallback model" hint="Used when the first provider fails">
                  <Input
                    value={form.fallback_model}
                    placeholder={d.llm.fallback?.model ?? ""}
                    disabled={!d.llm.fallback}
                    onChange={(e) => set("fallback_model", e.target.value)}
                  />
                </FormField>
              </div>
            </CardContent>
          </Card>

          {GROUPS.map((g) => (
            <Card key={g.title}>
              <CardHeader>
                <CardTitle>{g.title}</CardTitle>
                <CardDescription>{g.description}</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {g.fields.map((f) => (
                  <FormField key={f.key} id={f.key} label={f.label} hint={f.hint}>
                    <Input
                      type="number"
                      inputMode="decimal"
                      step={f.step ?? "1"}
                      min={f.min}
                      max={f.max}
                      value={String(form[f.key])}
                      onChange={(e) => set(f.key, Number(e.target.value) as never)}
                    />
                  </FormField>
                ))}
              </CardContent>
            </Card>
          ))}
          <div className="flex justify-end">
            <Button type="submit" variant="gradient" loading={save.isPending}>
              Save settings
            </Button>
          </div>
        </form>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plug className="size-4" aria-hidden /> Providers
              </CardTitle>
              <CardDescription>Set in the server&apos;s environment (.env).</CardDescription>
            </CardHeader>
            <CardContent className="divide-y pt-0">
              <ProviderRow title="Chat model" p={d.llm.primary} empty="LLM_PROVIDER not set — notes mode" />
              <ProviderRow title="Fallback" p={d.llm.fallback} empty="None (one retry instead)" />
              <ProviderRow title="Embeddings" p={d.embeddings} empty="EMBEDDING_PROVIDER not set — keyword search" />
            </CardContent>
            <CardContent className="flex flex-wrap gap-2 pt-0">
              <Button
                size="sm"
                variant="outline"
                disabled={!d.llm.primary?.ready}
                loading={test.isPending && test.variables === "chat"}
                onClick={() => test.mutate("chat")}
              >
                Test chat
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={!d.embeddings?.ready}
                loading={test.isPending && test.variables === "embedding"}
                onClick={() => test.mutate("embedding")}
              >
                Test embeddings
              </Button>
            </CardContent>
          </Card>
          <Alert variant="info">
            <KeyRound />
            <div className="space-y-1.5">
              <p className="font-medium">API keys stay in the environment</p>
              <p className="text-muted-foreground">
                Keys are never stored in the database or shown here. Set <code>LLM_PROVIDER</code>,{" "}
                <code>LLM_API_KEY</code> and optionally <code>EMBEDDING_PROVIDER</code> in <code>.env</code>, then
                restart the API.
              </p>
              <p className="text-muted-foreground">Providers: {d.providers.map((p) => p.label).join(", ")}.</p>
            </div>
          </Alert>
        </div>
      </div>
    </>
  );
}
