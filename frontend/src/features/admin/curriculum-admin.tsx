"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, FileQuestion } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/services/api";
import { contentApi } from "./content-api";

export function CurriculumAdmin() {
  const curricula = useQuery({ queryKey: ["admin", "curricula"], queryFn: contentApi.curricula });
  const [picked, setPicked] = useState<number | null>(null);
  const id = picked ?? curricula.data?.[0]?.id ?? null;
  const tree = useQuery({ queryKey: ["admin", "tree", id], queryFn: () => contentApi.tree(id!), enabled: id != null });
  const exp = useMutation({
    mutationFn: () => contentApi.exportCurriculum(id!),
    onSuccess: (data) => {
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const a = Object.assign(document.createElement("a"), { href: url, download: `curriculum-${id}.json` });
      a.click();
      URL.revokeObjectURL(url);
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Export failed"),
  });

  if (curricula.isLoading) return <LoadingState />;
  if (curricula.isError) return <ErrorState onRetry={() => void curricula.refetch()} />;
  if (!curricula.data?.length)
    return (
      <EmptyState title="No curricula yet" description="Load the sample with: python -m scripts.seed_sample_content" />
    );
  const cur = curricula.data.find((c) => c.id === id)!;

  return (
    <>
      <PageHeader
        title="Curriculum"
        description="Board / exam → class → subject → chapter → topic → concept, with prerequisites. Versions are kept so past activity stays linked to its syllabus."
        actions={
          <Button variant="outline" loading={exp.isPending} onClick={() => exp.mutate()}>
            <Download /> Export JSON
          </Button>
        }
      />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Select value={id ?? ""} onChange={(e) => setPicked(Number(e.target.value))} aria-label="Curriculum">
          {curricula.data.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.version})
            </option>
          ))}
        </Select>
        <Badge variant={cur.status === "published" ? "success" : "muted"}>{cur.status}</Badge>
        {cur.is_sample && <Badge variant="warning">Sample</Badge>}
        <span className="text-muted-foreground text-sm">
          {cur.board.name}
          {cur.grade && ` · ${cur.grade.name}`} · {cur.concept_count} concepts
        </span>
      </div>
      {tree.isLoading ? (
        <LoadingState />
      ) : (
        tree.data?.subjects.map((s) => (
          <Card key={s.id} className="mb-4">
            <CardHeader>
              <CardTitle>{s.name}</CardTitle>
              <CardDescription>{s.chapters.length} chapters</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {s.chapters.map((ch) => {
                const concepts = ch.topics.flatMap((t) => t.concepts);
                const names = new Map(concepts.map((c) => [c.id, c.name]));
                return (
                  <div key={ch.id}>
                    <p className="font-medium">
                      {ch.sequence + 1}. {ch.name}{" "}
                      <span className="text-muted-foreground text-xs font-normal">
                        {concepts.length} concepts · {concepts.reduce((n, c) => n + c.question_count, 0)} published
                        questions
                      </span>
                    </p>
                    {concepts.length > 0 && (
                      <ul className="mt-2 divide-y rounded-lg border">
                        {concepts.map((c) => (
                          <li key={c.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-sm">
                            <code className="bg-muted rounded px-1.5 text-xs">{c.code}</code>
                            <span className="flex-1">{c.name}</span>
                            {c.prerequisite_ids.length > 0 && (
                              <span className="text-muted-foreground text-xs">
                                needs {c.prerequisite_ids.map((p) => names.get(p) ?? `#${p}`).join(", ")}
                              </span>
                            )}
                            <Link
                              href={`/admin/questions?concept_id=${c.id}`}
                              className="text-primary inline-flex items-center gap-1 text-xs hover:underline"
                            >
                              <FileQuestion className="size-3.5" /> {c.question_count}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>
        ))
      )}
      <p className="text-muted-foreground text-xs">
        Editing chapters and concepts in this screen comes next; until then use the import/export API (
        <code>/api/v1/admin/curriculum/curricula/import</code>).
      </p>
    </>
  );
}
