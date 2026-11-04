import { api } from "@/services/api";
import type { Conversation, ConversationDetail, TutorMessage, TutorMode, TutorReply, TutorStatus } from "@/types/tutor";

export type Ask = {
  mode: TutorMode;
  message: string;
  conversation_id?: string;
  concept_id?: number;
  session_question_id?: string;
};

export const tutor = {
  status: () => api<TutorStatus>("/ai/tutor/status"),
  ask: (body: Ask) => api<TutorReply>("/ai/tutor/chat", { method: "POST", body }),
  hint: (session_question_id: string, conversation_id?: string) =>
    api<TutorReply>("/ai/tutor/hint", { method: "POST", body: { session_question_id, conversation_id } }),
  explain: (session_question_id: string, conversation_id?: string) =>
    api<TutorReply>("/ai/tutor/explain", { method: "POST", body: { session_question_id, conversation_id } }),
  conversations: () => api<Conversation[]>("/ai/tutor/conversations"),
  conversation: (id: string) => api<ConversationDetail>(`/ai/tutor/conversations/${id}`),
  remove: (id: string) => api<null>(`/ai/tutor/conversations/${id}`, { method: "DELETE" }),
  rate: (messageId: string, helpful: boolean | null) =>
    api<TutorMessage>(`/ai/tutor/messages/${messageId}/feedback`, { method: "POST", body: { helpful } }),
};
