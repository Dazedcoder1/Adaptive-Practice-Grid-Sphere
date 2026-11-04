import { api } from "@/services/api";
import type { Page } from "@/types/api";

export type ProviderStatus = { provider: string; label: string; model: string | null; ready: boolean } | null;

export type AiSettings = {
  tutor_enabled: boolean;
  chat_model: string;
  fallback_model: string;
  temperature: number;
  max_output_tokens: number;
  student_daily_messages: number;
  student_daily_tokens: number;
  platform_daily_cost_usd: number;
  input_price_per_mtok: number;
  output_price_per_mtok: number;
  embedding_price_per_mtok: number;
  retrieval_top_k: number;
  min_similarity: number;
  chunk_target_tokens: number;
  chunk_overlap_tokens: number;
  conversation_retention_days: number;
};

export type AiOverview = {
  llm: { primary: ProviderStatus; fallback: ProviderStatus };
  embeddings: (ProviderStatus & { dimensions?: number }) | null;
  providers: { id: string; label: string }[];
  effective_model: string | null;
  settings: AiSettings & { updated_at: string };
  documents: {
    documents: Record<"processing" | "review" | "approved" | "failed" | "archived", number>;
    approved_passages: number;
    embedded_passages: number;
  };
  today: { cost_usd: number; limit_usd: number };
};

export type DocStatus = "processing" | "review" | "approved" | "failed" | "archived";
export type SourceType = "notes" | "textbook" | "reference" | "solutions";
export type Licence = "owned" | "licensed" | "open" | "unknown";

export type RagDocument = {
  id: string;
  title: string;
  description: string;
  source_type: SourceType;
  licence: Licence;
  licence_note: string;
  curriculum_id: number;
  subject: { id: number; name: string | null };
  chapter: { id: number; name: string | null } | null;
  status: DocStatus;
  version: number;
  replaces_id: string | null;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  page_count: number | null;
  chunk_count: number;
  embedded_count: number;
  embedding_error: string | null;
  error: string | null;
  is_sample: boolean;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Passage = {
  id: number;
  ordinal: number;
  heading: string;
  page: number | null;
  text: string;
  token_count: number;
  concepts: { id: number; name: string }[];
  concepts_edited: boolean;
  embedded: boolean;
};

export type RagDocumentDetail = RagDocument & {
  concepts: { id: number; code: string; name: string }[];
  chunks: Passage[];
  chunks_page: number;
};

export type SearchHit = {
  chunk_id: number;
  document_id: string;
  title: string;
  source_type: string;
  heading: string;
  page: number | null;
  text: string;
  score: number;
  keyword_rank: number | null;
  similarity: number | null;
  concept_match: boolean;
};

export type EvalCase = {
  id: string;
  query: string;
  curriculum_id: number;
  subject_id: number | null;
  expected_document_id: string;
  expected_document_title: string | null;
  expected_phrase: string;
  created_at: string;
};

export type EvalRun = {
  id: string;
  k: number;
  retrieval: string;
  cases: number;
  hit_rate: number;
  mrr: number;
  results: { case_id: string; query: string; rank: number | null; top: { title: string; heading: string }[] }[];
  created_at: string;
};

export type PromptInfo = {
  key: string;
  label: string;
  default_body: string;
  active_version: number;
  active_body: string;
  versions: {
    version: number;
    body: string;
    note: string;
    is_active: boolean;
    created_at: string;
    activated_at: string | null;
  }[];
};

export type UsageReport = {
  days: number;
  today_cost_usd: number;
  daily_cost_limit_usd: number;
  prices_set: boolean;
  by_day: {
    day: string;
    calls: number;
    input_tokens: number;
    output_tokens: number;
    cost_usd: number;
    errors: number;
    fallbacks: number;
  }[];
  by_feature: {
    feature: string;
    calls: number;
    tokens: number;
    cost_usd: number;
    p50_ms: number;
    p95_ms: number;
    errors: number;
  }[];
  errors: { code: string; count: number }[];
  replies: { source: string; mode: string; count: number }[];
  helpful: { yes: number; no: number };
  flags: Record<string, number>;
};

const qs = (p: Record<string, string | number | undefined>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(p)) if (v !== undefined && v !== "") s.set(k, String(v));
  const str = s.toString();
  return str ? `?${str}` : "";
};

export const aiApi = {
  overview: () => api<AiOverview>("/admin/ai/overview"),
  saveSettings: (body: AiSettings) => api<AiSettings>("/admin/ai/settings", { method: "PUT", body }),
  test: (kind: "chat" | "embedding") =>
    api<{ ok: boolean; message: string }>("/admin/ai/test", { method: "POST", body: { kind } }),
  usage: (days: number) => api<UsageReport>(`/admin/ai/usage?days=${days}`),
  prompts: () => api<PromptInfo[]>("/admin/ai/prompts"),
  newPrompt: (key: string, body: string, note: string) =>
    api<PromptInfo[]>(`/admin/ai/prompts/${key}`, { method: "POST", body: { body, note } }),
  activatePrompt: (key: string, version: number) =>
    api<PromptInfo[]>(`/admin/ai/prompts/${key}/activate`, { method: "POST", body: { version } }),

  documents: (p: { status?: string; q?: string; page: number }) =>
    api<Page<RagDocument>>(`/admin/rag/documents${qs(p)}`),
  document: (id: string, page = 1) => api<RagDocumentDetail>(`/admin/rag/documents/${id}?page=${page}`),
  upload: (form: FormData) => api<RagDocumentDetail>("/admin/rag/documents", { method: "POST", body: form }),
  updateDocument: (
    id: string,
    body: Partial<Pick<RagDocument, "title" | "description" | "licence" | "licence_note" | "source_type">>,
  ) => api<RagDocumentDetail>(`/admin/rag/documents/${id}`, { method: "PATCH", body }),
  documentAction: (id: string, action: "approve" | "archive" | "reprocess" | "embed") =>
    api<RagDocumentDetail>(`/admin/rag/documents/${id}/${action}`, { method: "POST" }),
  setPassageConcepts: (id: number, concept_ids: number[]) =>
    api<{ id: number; concept_ids: number[] }>(`/admin/rag/chunks/${id}`, { method: "PATCH", body: { concept_ids } }),
  search: (body: {
    query: string;
    curriculum_id: number;
    subject_id?: number;
    concept_id?: number;
    k?: number;
    include_unapproved?: boolean;
  }) =>
    api<{ mode: string; embedding_error: string | null; hits: SearchHit[] }>("/admin/rag/search", {
      method: "POST",
      body,
    }),
  evalCases: () => api<EvalCase[]>("/admin/rag/eval-cases"),
  addEvalCase: (body: {
    query: string;
    curriculum_id: number;
    expected_document_id: string;
    expected_phrase: string;
  }) => api<EvalCase[]>("/admin/rag/eval-cases", { method: "POST", body }),
  deleteEvalCase: (id: string) => api<null>(`/admin/rag/eval-cases/${id}`, { method: "DELETE" }),
  runEval: (k: number) => api<EvalRun>(`/admin/rag/eval-runs?k=${k}`, { method: "POST" }),
  evalRuns: () => api<EvalRun[]>("/admin/rag/eval-runs"),
};
