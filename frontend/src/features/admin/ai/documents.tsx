"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileUp, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatRelative } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { aiApi, type DocStatus, type Licence, type SourceType } from "../ai-api";
import { contentApi } from "../content-api";
import { AiHeader } from "./ai-tabs";

const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong.");

export const DOC_STATUS: Record<
  DocStatus,
  { label: string; variant: "success" | "warning" | "destructive" | "muted" }
> = {
  processing: { label: "Processing", variant: "muted" },
  review: { label: "Needs review", variant: "warning" },
  approved: { label: "Approved", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
  archived: { label: "Archived", variant: "muted" },
};
export const SOURCE_TYPES: Record<SourceType, string> = {
  notes: "Study notes",
  textbook: "Textbook",
  reference: "Reference",
  solutions: "Worked solutions",
};
export const LICENCES: Record<Licence, string> = {
  owned: "Written by us",
  licensed: "Licensed",
  open: "Open licence",
  unknown: "Unknown — can't be approved",
};

export function UploadDialog({ replacesId, onDone }: { replacesId?: string; onDone?: (id: string) => void }) {
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [pickedCurriculum, setCurriculumId] = useState<number | "">("");
  const [pickedSubject, setSubjectId] = useState<number | "">("");
  const [chapterId, setChapterId] = useState<number | "">("");
  const [sourceType, setSourceType] = useState<SourceType>("notes");
  const [licence, setLicence] = useState<Licence>("owned");
  const [licenceNote, setLicenceNote] = useState("");

  const curricula = useQuery({ queryKey: ["admin", "curricula"], queryFn: contentApi.curricula, enabled: open });
  const curriculumId = pickedCurriculum === "" ? (curricula.data?.[0]?.id ?? "") : pickedCurriculum;
  const tree = useQuery({
    queryKey: ["admin", "tree", curriculumId],
    queryFn: () => contentApi.tree(Number(curriculumId)),
    enabled: open && curriculumId !== "",
  });
  const subjects = tree.data?.subjects ?? [];
  const subjectId: number | "" = pickedSubject !== "" ? pickedSubject : subjects.length ? subjects[0].id : "";
  const chapters = subjects.find((s) => s.id === subjectId)?.chapters ?? [];

  const upload = useMutation({
    mutationFn: () => {
      const f = new FormData();
      f.set("file", file!);
      f.set("title", title || file!.name);
      f.set("curriculum_id", String(curriculumId));
      f.set("subject_id", String(subjectId));
      if (chapterId !== "") f.set("chapter_id", String(chapterId));
      f.set("source_type", sourceType);
      f.set("licence", licence);
      f.set("licence_note", licenceNote);
      if (replacesId) f.set("replaces_id", replacesId);
      return aiApi.upload(f);
    },
    onSuccess: (d) => {
      toast.success(`Processed into ${d.chunk_count} passages — review and approve it.`);
      void qc.invalidateQueries({ queryKey: ["admin", "rag"] });
      setOpen(false);
      if (onDone) onDone(d.id);
      else router.push(`/admin/ai/documents/${d.id}`);
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={replacesId ? "outline" : "gradient"} size={replacesId ? "sm" : "default"}>
          <FileUp /> {replacesId ? "Upload new version" : "Upload document"}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{replacesId ? "Upload a new version" : "Upload study material"}</DialogTitle>
          <DialogDescription>
            PDF, Word (.docx), Markdown or text, up to 15 MB. It&apos;s split into passages and mapped to concepts;
            nothing reaches students until you approve it.
          </DialogDescription>
        </DialogHeader>
        <form
          id="upload-form"
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (file) upload.mutate();
          }}
        >
          <FormField id="doc-file" label="File">
            <Input
              type="file"
              accept=".pdf,.docx,.md,.markdown,.txt"
              onChange={(e) => {
                const f = e.target.files?.[0] ?? null;
                setFile(f);
                if (f && !title) setTitle(f.name.replace(/\.[^.]+$/, ""));
              }}
            />
          </FormField>
          <FormField id="doc-title" label="Title">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
          </FormField>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField id="doc-curriculum" label="Curriculum">
              <Select
                value={curriculumId}
                onChange={(e) => {
                  setCurriculumId(Number(e.target.value));
                  setSubjectId("");
                  setChapterId("");
                }}
              >
                {curricula.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField id="doc-subject" label="Subject">
              <Select
                value={subjectId}
                onChange={(e) => {
                  setSubjectId(Number(e.target.value));
                  setChapterId("");
                }}
              >
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>
          <FormField id="doc-chapter" label="Chapter" hint="Optional — narrows concept mapping to one chapter">
            <Select value={chapterId} onChange={(e) => setChapterId(e.target.value ? Number(e.target.value) : "")}>
              <option value="">Whole subject</option>
              {chapters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </FormField>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField id="doc-type" label="Type">
              <Select value={sourceType} onChange={(e) => setSourceType(e.target.value as SourceType)}>
                {Object.entries(SOURCE_TYPES).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField id="doc-licence" label="Licence">
              <Select value={licence} onChange={(e) => setLicence(e.target.value as Licence)}>
                {Object.entries(LICENCES).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>
          <FormField id="doc-licence-note" label="Licence note" hint="Source, agreement or licence name">
            <Input value={licenceNote} onChange={(e) => setLicenceNote(e.target.value)} maxLength={500} />
          </FormField>
        </form>
        <DialogFooter>
          <Button
            type="submit"
            form="upload-form"
            variant="gradient"
            disabled={!file || subjectId === ""}
            loading={upload.isPending}
          >
            Upload & process
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function AiDocumentsPage() {
  const router = useRouter();
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const list = useQuery({
    queryKey: ["admin", "rag", "documents", status, q, page],
    queryFn: () => aiApi.documents({ status, q: q.trim(), page }),
    placeholderData: keepPreviousData,
  });

  return (
    <>
      <AiHeader actions={<UploadDialog />} />
      <Card>
        <div className="flex flex-col gap-3 border-b p-4 md:flex-row">
          <div className="relative flex-1">
            <Search className="text-muted-foreground absolute top-1/2 left-3 size-4 -translate-y-1/2" aria-hidden />
            <Input
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
              placeholder="Search titles"
              className="pl-9"
              aria-label="Search documents"
            />
          </div>
          <Select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            aria-label="Status"
          >
            <option value="">Any status</option>
            {Object.entries(DOC_STATUS).map(([k, v]) => (
              <option key={k} value={k}>
                {v.label}
              </option>
            ))}
          </Select>
        </div>
        {list.isLoading ? (
          <LoadingState />
        ) : list.isError ? (
          <ErrorState message={errMsg(list.error)} onRetry={() => void list.refetch()} />
        ) : !list.data?.items.length ? (
          <EmptyState title="No documents" description="Upload study notes, textbook chapters or worked solutions." />
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Document</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="hidden md:table-cell">Passages</TableHead>
                  <TableHead className="hidden lg:table-cell">Licence</TableHead>
                  <TableHead className="hidden lg:table-cell">Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.data.items.map((d) => (
                  <TableRow
                    key={d.id}
                    className="cursor-pointer"
                    onClick={() => router.push(`/admin/ai/documents/${d.id}`)}
                  >
                    <TableCell>
                      <p className="font-medium">{d.title}</p>
                      <p className="text-muted-foreground text-xs">
                        {SOURCE_TYPES[d.source_type]} · {d.subject.name}
                        {d.chapter ? ` › ${d.chapter.name}` : ""} · v{d.version}
                        {d.is_sample && " · sample"}
                      </p>
                    </TableCell>
                    <TableCell>
                      <Badge variant={DOC_STATUS[d.status].variant}>{DOC_STATUS[d.status].label}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground hidden text-sm md:table-cell">
                      {d.chunk_count}
                      {d.embedded_count > 0 && ` · ${d.embedded_count} embedded`}
                    </TableCell>
                    <TableCell className="text-muted-foreground hidden text-xs lg:table-cell">
                      {LICENCES[d.licence]}
                    </TableCell>
                    <TableCell className="text-muted-foreground hidden text-xs lg:table-cell">
                      {formatRelative(d.updated_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={page} pageSize={20} total={list.data.total} onPage={setPage} />
          </>
        )}
      </Card>
    </>
  );
}
