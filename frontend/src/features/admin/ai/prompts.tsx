"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { History, Lock } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ErrorState, LoadingState } from "@/components/feedback/states";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { formatRelative } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { aiApi, type PromptInfo } from "../ai-api";
import { AiHeader } from "./ai-tabs";

const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong.");

function PromptCard({ p }: { p: PromptInfo }) {
  const qc = useQueryClient();
  const [draft, setDraft] = useState(p.active_body);
  const [note, setNote] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const update = (data: PromptInfo[]) => qc.setQueryData(["admin", "ai", "prompts"], data);
  const create = useMutation({
    mutationFn: () => aiApi.newPrompt(p.key, draft, note),
    onSuccess: (d) => {
      update(d);
      setNote("");
      toast.success("Saved as a new version — activate it to use it.");
    },
    onError: (e) => toast.error(errMsg(e)),
  });
  const activate = useMutation({
    mutationFn: (v: number) => aiApi.activatePrompt(p.key, v),
    onSuccess: (d, v) => {
      update(d);
      const next = d.find((x) => x.key === p.key);
      if (next) setDraft(next.active_body);
      toast.success(v ? `Version ${v} is live` : "Back to the built-in default");
    },
    onError: (e) => toast.error(errMsg(e)),
  });
  const changed = draft.trim() !== p.active_body.trim();

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>{p.label}</CardTitle>
          <CardDescription>
            <code className="text-xs">{p.key}</code> · live:{" "}
            {p.active_version ? `version ${p.active_version}` : "built-in default"}
          </CardDescription>
        </div>
        <Button size="sm" variant="ghost" onClick={() => setShowHistory((s) => !s)} aria-expanded={showHistory}>
          <History /> {p.versions.length} versions
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        <label htmlFor={`prompt-${p.key}`} className="sr-only">
          {p.label} instructions
        </label>
        <textarea
          id={`prompt-${p.key}`}
          rows={5}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="border-input bg-card w-full rounded-lg border p-3 font-mono text-[13px] leading-relaxed"
        />
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <FormField id={`note-${p.key}`} label="Change note" className="flex-1">
            <Input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={300}
              placeholder="What changed and why"
            />
          </FormField>
          <Button variant="outline" disabled={!changed} loading={create.isPending} onClick={() => create.mutate()}>
            Save new version
          </Button>
        </div>
        {showHistory && (
          <ul className="divide-y rounded-lg border text-sm">
            <li className="flex items-center gap-3 px-3 py-2">
              <span className="flex-1">Built-in default</span>
              {p.active_version === 0 ? (
                <Badge variant="success">Live</Badge>
              ) : (
                <Button size="sm" variant="ghost" onClick={() => activate.mutate(0)}>
                  Use default
                </Button>
              )}
            </li>
            {p.versions.map((v) => (
              <li key={v.version} className="flex items-start gap-3 px-3 py-2">
                <div className="min-w-0 flex-1">
                  <p>
                    Version {v.version}
                    <span className="text-muted-foreground"> · {formatRelative(v.created_at)}</span>
                  </p>
                  {v.note && <p className="text-muted-foreground text-xs">{v.note}</p>}
                  <p className="text-muted-foreground mt-1 line-clamp-2 font-mono text-xs">{v.body}</p>
                </div>
                {v.is_active ? (
                  <Badge variant="success">Live</Badge>
                ) : (
                  <Button size="sm" variant="ghost" onClick={() => activate.mutate(v.version)}>
                    Make live
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function AiPromptsPage() {
  const prompts = useQuery({ queryKey: ["admin", "ai", "prompts"], queryFn: aiApi.prompts });
  return (
    <>
      <AiHeader />
      <Alert variant="info" className="mb-6">
        <Lock />
        <span>
          These set the tutor&apos;s teaching style. Safety rules — treating student text and documents as data, never
          revealing an answer before the student tries, citing only real sources — are added by the system to every
          request and can&apos;t be edited here. Every tutor reply records which prompt versions produced it.
        </span>
      </Alert>
      {prompts.isLoading ? (
        <LoadingState />
      ) : prompts.isError || !prompts.data ? (
        <ErrorState message={errMsg(prompts.error)} onRetry={() => void prompts.refetch()} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {prompts.data.map((p) => (
            <PromptCard key={`${p.key}:${p.active_version}`} p={p} />
          ))}
        </div>
      )}
    </>
  );
}
