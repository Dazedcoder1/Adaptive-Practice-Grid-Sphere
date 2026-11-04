"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, ArrowLeft, CheckCircle2, Cpu, Pencil, RefreshCw, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { ErrorState, LoadingState } from "@/components/feedback/states";
import { Markdown } from "@/components/questions/markdown";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { FormField } from "@/components/ui/form-field";
import { Select } from "@/components/ui/select";
import { formatRelative } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { aiApi, type Licence, type Passage, type RagDocumentDetail } from "../ai-api";
import { AiHeader } from "./ai-tabs";
import { DOC_STATUS, LICENCES, SOURCE_TYPES, UploadDialog } from "./documents";

const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong.");
const kb = (n: number) => (n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(n / 1024)} KB`);

function ConceptEditor({ passage, doc }: { passage: Passage; doc: RagDocumentDetail }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [chosen, setChosen] = useState<number[]>(passage.concepts.map((c) => c.id));
  const save = useMutation({
    mutationFn: () => aiApi.setPassageConcepts(passage.id, chosen),
    onSuccess: () => {
      toast.success("Concepts updated");
      setOpen(false);
      void qc.invalidateQueries({ queryKey: ["admin", "rag", "document", doc.id] });
    },
    onError: (e) => toast.error(errMsg(e)),
  });
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="ghost" aria-label={`Edit concepts for passage ${passage.ordinal + 1}`}>
          <Pencil /> Concepts
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Concepts for this passage</DialogTitle>
          <DialogDescription>
            The tutor prefers passages tagged with the concept a student is working on.
          </DialogDescription>
        </DialogHeader>
        <ul className="max-h-80 space-y-2 overflow-y-auto">
          {doc.concepts.map((c) => (
            <li key={c.id}>
              <label className="flex items-center gap-2.5 text-sm">
                <Checkbox
                  checked={chosen.includes(c.id)}
                  onCheckedChange={(v) =>
                    setChosen((xs) => (v === true ? [...xs, c.id].slice(0, 6) : xs.filter((x) => x !== c.id)))
                  }
                />
                {c.name} <span className="text-muted-foreground text-xs">{c.code}</span>
              </label>
            </li>
          ))}
        </ul>
        <DialogFooter>
          <Button variant="gradient" loading={save.isPending} onClick={() => save.mutate()}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function AiDocumentDetail({ id }: { id: string }) {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const doc = useQuery({
    queryKey: ["admin", "rag", "document", id, page],
    queryFn: () => aiApi.document(id, page),
  });
  const refresh = () => void qc.invalidateQueries({ queryKey: ["admin", "rag"] });
  const act = useMutation({
    mutationFn: (a: "approve" | "archive" | "reprocess" | "embed") => aiApi.documentAction(id, a),
    onSuccess: (_, a) => {
      toast.success(
        {
          approve: "Approved — students can now get answers from it.",
          archive: "Archived",
          reprocess: "Re-processed — review the passages again.",
          embed: "Embedding started",
        }[a],
      );
      refresh();
    },
    onError: (e) => toast.error(errMsg(e)),
  });
  const setLicence = useMutation({
    mutationFn: (licence: Licence) => aiApi.updateDocument(id, { licence }),
    onSuccess: refresh,
    onError: (e) => toast.error(errMsg(e)),
  });

  if (doc.isLoading) return <LoadingState />;
  if (doc.isError || !doc.data) return <ErrorState message={errMsg(doc.error)} onRetry={() => void doc.refetch()} />;
  const d = doc.data;
  const st = DOC_STATUS[d.status];
  const pages = Math.ceil(d.chunk_count / 50);

  return (
    <>
      <AiHeader />
      <Link
        href="/admin/ai/documents"
        className="text-muted-foreground hover:text-foreground mb-4 inline-flex items-center gap-1.5 text-sm"
      >
        <ArrowLeft className="size-4" /> Documents
      </Link>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-semibold">{d.title}</h2>
            <Badge variant={st.variant}>{st.label}</Badge>
            {d.is_sample && <Badge variant="outline">Sample</Badge>}
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            {SOURCE_TYPES[d.source_type]} · {d.subject.name}
            {d.chapter ? ` › ${d.chapter.name}` : ""} · version {d.version} · {d.file_name} ({kb(d.size_bytes)}
            {d.page_count ? `, ${d.page_count} pages` : ""}) · updated {formatRelative(d.updated_at)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(d.status === "review" || d.status === "archived") && (
            <Button
              variant="gradient"
              disabled={d.licence === "unknown"}
              loading={act.isPending && act.variables === "approve"}
              onClick={() => act.mutate("approve")}
            >
              <CheckCircle2 /> Approve for students
            </Button>
          )}
          <Button
            variant="outline"
            loading={act.isPending && act.variables === "reprocess"}
            onClick={() => act.mutate("reprocess")}
          >
            <RefreshCw /> Re-process
          </Button>
          <Button
            variant="outline"
            loading={act.isPending && act.variables === "embed"}
            onClick={() => act.mutate("embed")}
          >
            <Cpu /> Embed
          </Button>
          {d.status !== "archived" && (
            <Button
              variant="ghost"
              loading={act.isPending && act.variables === "archive"}
              onClick={() => act.mutate("archive")}
            >
              <Archive /> Archive
            </Button>
          )}
          <UploadDialog replacesId={d.id} />
        </div>
      </div>

      <div className="mb-6 grid gap-4 lg:grid-cols-3">
        <Card className="p-4">
          <p className="text-muted-foreground text-sm">Passages</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{d.chunk_count}</p>
        </Card>
        <Card className="p-4">
          <p className="text-muted-foreground text-sm">With semantic vectors</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">
            {d.embedded_count} <span className="text-muted-foreground text-sm font-normal">of {d.chunk_count}</span>
          </p>
          {d.embedding_error && <p className="text-destructive mt-1 text-xs">{d.embedding_error}</p>}
        </Card>
        <Card className="p-4">
          <FormField id="licence" label="Licence" hint={d.licence_note || "Unknown licences can't be approved."}>
            <Select value={d.licence} onChange={(e) => setLicence.mutate(e.target.value as Licence)}>
              {Object.entries(LICENCES).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Select>
          </FormField>
        </Card>
      </div>

      {d.error && (
        <Alert variant="destructive" className="mb-4">
          <TriangleAlert />
          <span>{d.error}</span>
        </Alert>
      )}
      {d.status === "review" && (
        <Alert variant="warning" className="mb-4">
          <TriangleAlert />
          <span>
            Check the passages and their concepts below, then approve. Until then the tutor won&apos;t use this
            document.
          </span>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Passages</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {d.chunks.map((c) => (
            <div key={c.id} className="rounded-lg border p-3">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <Badge variant="muted">#{c.ordinal + 1}</Badge>
                <span className="text-sm font-medium">{c.heading.split(" › ").at(-1) || "Untitled section"}</span>
                {c.page && <span className="text-muted-foreground text-xs">page {c.page}</span>}
                <span className="text-muted-foreground text-xs">~{c.token_count} tokens</span>
                {c.embedded && <Badge variant="blue">Embedded</Badge>}
                <span className="ml-auto flex flex-wrap items-center gap-1">
                  {c.concepts.length ? (
                    c.concepts.map((x) => (
                      <Badge key={x.id} variant={c.concepts_edited ? "default" : "outline"}>
                        {x.name}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-muted-foreground text-xs">No concepts</span>
                  )}
                  <ConceptEditor passage={c} doc={d} />
                </span>
              </div>
              <Markdown className="text-muted-foreground line-clamp-6 text-[13px]">{c.text}</Markdown>
            </div>
          ))}
          {pages > 1 && (
            <div className="flex justify-center gap-2 pt-2">
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Previous
              </Button>
              <span className="text-muted-foreground self-center text-sm">
                Page {page} of {pages}
              </span>
              <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>
                Next
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}
