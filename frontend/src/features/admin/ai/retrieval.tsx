"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FlaskConical, Play, Search, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/feedback/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Markdown } from "@/components/questions/markdown";
import { formatRelative, inlineMaths } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { aiApi, type SearchHit } from "../ai-api";
import { contentApi } from "../content-api";
import { AiHeader } from "./ai-tabs";

const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong.");
const pct = (x: number) => `${Math.round(x * 100)}%`;

function Hit({ h, i }: { h: SearchHit; i: number }) {
  return (
    <li className="rounded-lg border p-3">
      <div className="mb-1.5 flex flex-wrap items-center gap-2 text-sm">
        <Badge variant="muted">{i + 1}</Badge>
        <span className="font-medium">{h.heading.split(" › ").at(-1) || h.title}</span>
        <span className="text-muted-foreground text-xs">
          {h.title}
          {h.page ? ` · p. ${h.page}` : ""}
        </span>
        <span className="text-muted-foreground ml-auto flex flex-wrap gap-1.5 text-xs tabular-nums">
          {h.keyword_rank && <Badge variant="outline">keyword #{h.keyword_rank}</Badge>}
          {h.similarity !== null && <Badge variant="outline">similarity {h.similarity.toFixed(2)}</Badge>}
          {h.concept_match && <Badge variant="blue">concept match</Badge>}
          <Badge variant="default">score {h.score.toFixed(4)}</Badge>
        </span>
      </div>
      <Markdown className="text-muted-foreground line-clamp-3 text-[13px]">{inlineMaths(h.text)}</Markdown>
    </li>
  );
}

export function AiRetrievalPage() {
  const qc = useQueryClient();
  const curricula = useQuery({ queryKey: ["admin", "curricula"], queryFn: contentApi.curricula });
  const [picked, setCurriculumId] = useState<number | "">("");
  const curriculumId = picked === "" ? (curricula.data?.[0]?.id ?? "") : picked;
  const [query, setQuery] = useState("");
  const [unapproved, setUnapproved] = useState(false);

  const search = useMutation({
    mutationFn: () =>
      aiApi.search({ query, curriculum_id: Number(curriculumId), k: 5, include_unapproved: unapproved }),
    onError: (e) => toast.error(errMsg(e)),
  });

  const docs = useQuery({
    queryKey: ["admin", "rag", "documents", "approved"],
    queryFn: () => aiApi.documents({ status: "approved", page: 1 }),
  });
  const cases = useQuery({ queryKey: ["admin", "rag", "eval-cases"], queryFn: aiApi.evalCases });
  const runs = useQuery({ queryKey: ["admin", "rag", "eval-runs"], queryFn: aiApi.evalRuns });
  const [caseQuery, setCaseQuery] = useState("");
  const [caseDoc, setCaseDoc] = useState("");
  const [casePhrase, setCasePhrase] = useState("");
  const addCase = useMutation({
    mutationFn: () =>
      aiApi.addEvalCase({
        query: caseQuery,
        curriculum_id: Number(curriculumId),
        expected_document_id: caseDoc,
        expected_phrase: casePhrase,
      }),
    onSuccess: () => {
      setCaseQuery("");
      setCasePhrase("");
      void qc.invalidateQueries({ queryKey: ["admin", "rag", "eval-cases"] });
    },
    onError: (e) => toast.error(errMsg(e)),
  });
  const delCase = useMutation({
    mutationFn: (id: string) => aiApi.deleteEvalCase(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin", "rag", "eval-cases"] }),
  });
  const run = useMutation({
    mutationFn: () => aiApi.runEval(4),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin", "rag", "eval-runs"] }),
    onError: (e) => toast.error(errMsg(e)),
  });
  const last = run.data ?? runs.data?.[0];

  return (
    <>
      <AiHeader />
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="size-4" aria-hidden /> Try a query
            </CardTitle>
            <CardDescription>
              See exactly which passages the tutor would get, and why they ranked where they did.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (query.trim() && curriculumId !== "") search.mutate();
              }}
            >
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g. why does a car need friction to turn?"
                  aria-label="Query"
                />
                <Button type="submit" variant="gradient" loading={search.isPending} disabled={!query.trim()}>
                  Search
                </Button>
              </div>
              <div className="flex flex-wrap items-center gap-4">
                <Select
                  value={curriculumId}
                  onChange={(e) => setCurriculumId(Number(e.target.value))}
                  aria-label="Curriculum"
                  className="max-w-xs"
                >
                  {curricula.data?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </Select>
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox checked={unapproved} onCheckedChange={(v) => setUnapproved(v === true)} />
                  Include documents awaiting review
                </label>
              </div>
            </form>
            {search.data && (
              <>
                <p className="text-muted-foreground text-xs">
                  Retrieval:{" "}
                  <strong className="text-foreground">
                    {search.data.mode === "hybrid" ? "hybrid (keyword + semantic)" : "keyword only"}
                  </strong>
                  {search.data.embedding_error && ` · semantic search failed (${search.data.embedding_error})`}
                </p>
                {search.data.hits.length ? (
                  <ol className="space-y-2">
                    {search.data.hits.map((h, i) => (
                      <Hit key={h.chunk_id} h={h} i={i} />
                    ))}
                  </ol>
                ) : (
                  <EmptyState title="No passages matched" description="Students asking this would get no sources." />
                )}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="size-4" aria-hidden /> Retrieval evaluation
            </CardTitle>
            <CardDescription>
              Test queries with a known right source. Re-run after changing content, chunk sizes or the embedding model.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <form
              className="grid gap-3 sm:grid-cols-2"
              onSubmit={(e) => {
                e.preventDefault();
                if (caseQuery.trim().length >= 3 && caseDoc) addCase.mutate();
              }}
            >
              <FormField id="case-query" label="Test query" className="sm:col-span-2">
                <Input value={caseQuery} onChange={(e) => setCaseQuery(e.target.value)} maxLength={500} />
              </FormField>
              <FormField id="case-doc" label="Should come from">
                <Select value={caseDoc} onChange={(e) => setCaseDoc(e.target.value)}>
                  <option value="">Choose a document</option>
                  {docs.data?.items.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.title}
                    </option>
                  ))}
                </Select>
              </FormField>
              <FormField id="case-phrase" label="Passage contains (optional)">
                <Input value={casePhrase} onChange={(e) => setCasePhrase(e.target.value)} maxLength={200} />
              </FormField>
              <div className="sm:col-span-2">
                <Button type="submit" size="sm" variant="outline" loading={addCase.isPending} disabled={!caseDoc}>
                  Add test query
                </Button>
              </div>
            </form>

            {cases.data?.length ? (
              <ul className="divide-y rounded-lg border text-sm">
                {cases.data.map((c) => {
                  const r = last?.results.find((x) => x.case_id === c.id);
                  return (
                    <li key={c.id} className="flex items-center gap-3 px-3 py-2">
                      <div className="min-w-0 flex-1">
                        <p className="truncate">{c.query}</p>
                        <p className="text-muted-foreground truncate text-xs">
                          → {c.expected_document_title}
                          {c.expected_phrase && ` · “${c.expected_phrase}”`}
                        </p>
                      </div>
                      {r &&
                        (r.rank ? (
                          <Badge variant="success">rank {r.rank}</Badge>
                        ) : (
                          <Badge variant="destructive">missed</Badge>
                        ))}
                      <Button
                        size="icon"
                        variant="ghost"
                        className="size-7"
                        aria-label={`Delete test query “${c.query}”`}
                        onClick={() => delCase.mutate(c.id)}
                      >
                        <Trash2 />
                      </Button>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-muted-foreground text-sm">No test queries yet.</p>
            )}

            <div className="flex flex-wrap items-center gap-3">
              <Button
                variant="gradient"
                size="sm"
                loading={run.isPending}
                disabled={!cases.data?.length}
                onClick={() => run.mutate()}
              >
                <Play /> Run evaluation
              </Button>
              {last && (
                <p className="text-sm">
                  Hit rate <strong>{pct(last.hit_rate)}</strong> · MRR <strong>{last.mrr.toFixed(2)}</strong> ·{" "}
                  <span className="text-muted-foreground">
                    top {last.k}, {last.retrieval}, {formatRelative(last.created_at)}
                  </span>
                </p>
              )}
            </div>
            {runs.data && runs.data.length > 1 && (
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Run</TableHead>
                    <TableHead>Queries</TableHead>
                    <TableHead>Hit rate</TableHead>
                    <TableHead>MRR</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.data.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="text-muted-foreground text-xs">{formatRelative(r.created_at)}</TableCell>
                      <TableCell>{r.cases}</TableCell>
                      <TableCell>{pct(r.hit_rate)}</TableCell>
                      <TableCell>{r.mrr.toFixed(2)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
