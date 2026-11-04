import { api } from "@/services/api";
import type { CurriculumTree, QuestionContent, QuestionType } from "@/types/learning";
import type { Page } from "@/types/api";

export type QStatus = "draft" | "in_review" | "rejected" | "published" | "archived";

export type QuestionRow = {
  id: string;
  status: QStatus;
  type: QuestionType;
  difficulty: number;
  stem: string;
  version: number;
  is_sample: boolean;
  concepts: string[];
  attempts: number;
  updated_at: string;
};

export type Answer = {
  correct?: string | string[];
  partial?: boolean;
  value?: number;
  tolerance?: number;
  accepted?: string[][];
  pairs?: Record<string, string>;
  model_answer?: string;
};

export type QuestionVersion = {
  id: string;
  version: number;
  status: string;
  type: QuestionType;
  difficulty: number;
  stem: string;
  content: QuestionContent;
  answer: Answer;
  solution: string;
  hints: string[];
  estimated_seconds: number;
  source: string | null;
  created_at: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  published_at: string | null;
};

export type QuestionDetail = {
  id: string;
  status: QStatus;
  is_sample: boolean;
  published_version_id: string | null;
  latest: QuestionVersion;
  versions: {
    id: string;
    version: number;
    status: string;
    created_at: string;
    published_at: string | null;
    review_note: string | null;
  }[];
  concepts: { id: number; code: string; name: string; chapter: { id: number; name: string }; weight: number }[];
  archived_at: string | null;
  created_at: string;
  attempts: number;
  correct_rate: number | null;
};

export type QuestionInput = {
  type: QuestionType;
  difficulty: number;
  stem: string;
  content: QuestionContent;
  answer: Answer;
  solution: string;
  hints: string[];
  estimated_seconds: number;
  source: string | null;
  concepts: { concept_id: number; weight: number }[];
};

export type CurriculumRow = {
  id: number;
  name: string;
  version: string;
  status: string;
  is_sample: boolean;
  board: { id: number; name: string };
  grade: { id: number; name: string } | null;
  concept_count: number;
};

const qs = (p: Record<string, string | number | undefined>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(p)) if (v !== undefined && v !== "") s.set(k, String(v));
  const str = s.toString();
  return str ? `?${str}` : "";
};

export const contentApi = {
  questions: (p: {
    q?: string;
    status?: string;
    type?: string;
    difficulty?: string;
    concept_id?: string;
    page: number;
  }) => api<Page<QuestionRow>>(`/admin/questions${qs(p)}`),
  stats: () =>
    api<{ questions_total: number; questions_published: number; approval_backlog: number }>("/admin/questions/stats"),
  question: (id: string) => api<QuestionDetail>(`/admin/questions/${id}`),
  create: (body: QuestionInput) => api<QuestionDetail>("/admin/questions", { method: "POST", body }),
  save: (id: string, body: QuestionInput) => api<QuestionDetail>(`/admin/questions/${id}`, { method: "PUT", body }),
  action: (id: string, action: "submit" | "publish" | "reject" | "archive" | "restore", note?: string) =>
    api<QuestionDetail>(`/admin/questions/${id}/${action}`, {
      method: "POST",
      body: action === "publish" || action === "reject" ? { note } : undefined,
    }),
  curricula: () => api<CurriculumRow[]>("/admin/curriculum/curricula"),
  tree: (id: number) => api<CurriculumTree>(`/admin/curriculum/curricula/${id}/tree`),
  exportCurriculum: (id: number) => api<unknown>(`/admin/curriculum/curricula/${id}/export`),
};
