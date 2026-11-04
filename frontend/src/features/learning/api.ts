import { api } from "@/services/api";
import type { StudentProfile } from "@/types/api";
import type {
  ConceptDetail,
  ConceptRef,
  CurriculumTree,
  Dashboard,
  Delivery,
  Feedback,
  MistakeCategory,
  NotebookEntry,
  OnboardingOptions,
  Recommendation,
  Response,
  RevisionItem,
  SessionMode,
  SessionReport,
  SessionSummary,
  WeakConcept,
} from "@/types/learning";

export type StartSession = {
  mode: SessionMode;
  subject_id?: number;
  chapter_id?: number;
  topic_id?: number;
  concept_ids?: number[];
  question_ids?: string[];
  count?: number;
};

export const learning = {
  options: () => api<OnboardingOptions>("/curriculum/options"),
  saveOnboarding: (body: {
    study_mode: string;
    curriculum_id: number;
    subject_ids: number[];
    goals: string[];
    target_exam_date: string | null;
    weekly_days: number | null;
    minutes_per_day: number | null;
  }) => api<StudentProfile>("/students/me/onboarding", { method: "PUT", body }),
  myCurriculum: () => api<CurriculumTree>("/curriculum/mine"),
  concept: (id: number) => api<ConceptDetail>(`/curriculum/concepts/${id}`),
  search: (q: string) => api<ConceptRef[]>(`/curriculum/search?q=${encodeURIComponent(q)}`),

  startSession: (body: StartSession) => api<SessionSummary>("/practice/sessions", { method: "POST", body }),
  sessions: (status?: "open" | "completed") =>
    api<SessionSummary[]>(`/practice/sessions${status ? `?status=${status}` : ""}`),
  session: (id: string) => api<SessionSummary>(`/practice/sessions/${id}`),
  next: (id: string) => api<Delivery>(`/practice/sessions/${id}/next`, { method: "POST" }),
  hint: (sessionId: string, sqId: string) =>
    api<{ hints: string[]; hints_available: number }>(`/practice/sessions/${sessionId}/questions/${sqId}/hint`, {
      method: "POST",
    }),
  submit: (sqId: string, response: Response, idempotencyKey: string) =>
    api<Feedback>("/practice/attempts", {
      method: "POST",
      body: { session_question_id: sqId, response },
      idempotencyKey,
    }),
  lifecycle: (id: string, action: "pause" | "resume" | "complete") =>
    api<SessionSummary>(`/practice/sessions/${id}/${action}`, { method: "POST" }),
  report: (id: string) => api<SessionReport>(`/practice/sessions/${id}/report`),

  dashboard: () => api<Dashboard>("/analytics/dashboard"),
  recommendations: () => api<Recommendation[]>("/adaptive/recommendations"),
  weak: () => api<WeakConcept[]>("/adaptive/weak-concepts"),
  revision: () => api<{ due: RevisionItem[]; upcoming: RevisionItem[] }>("/revision/queue"),

  notebook: (params: { status?: string; category?: string } = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]).toString();
    return api<NotebookEntry[]>(`/error-notebook${qs ? `?${qs}` : ""}`);
  },
  saveToNotebook: (question_id: string, note?: string) =>
    api<NotebookEntry>("/error-notebook", { method: "POST", body: { question_id, note } }),
  updateEntry: (id: string, body: { category?: MistakeCategory; note?: string; status?: "open" | "resolved" }) =>
    api<NotebookEntry>(`/error-notebook/${id}`, { method: "PATCH", body }),
  deleteEntry: (id: string) => api<null>(`/error-notebook/${id}`, { method: "DELETE" }),
};
