export type TutorMode = "teach" | "hint" | "solve" | "test" | "mistake";

/** How a tutor reply was produced: the AI, study notes only, or a fixed wellbeing reply. */
export type ReplySource = "ai" | "notes" | "safety";

export type Citation = {
  id: string;
  chunk_id: number;
  document_id: string;
  title: string;
  heading: string;
  page: number | null;
  excerpt: string;
};

export type TutorAction = { type: "practice"; concept_id: number; label: string };

export type TutorMessage = {
  id: string;
  role: "student" | "tutor";
  mode: TutorMode;
  content: string;
  source: ReplySource | null;
  citations: Citation[];
  flags: string[];
  actions: TutorAction[];
  helpful: boolean | null;
  created_at: string;
};

export type Conversation = {
  id: string;
  title: string;
  mode: TutorMode;
  concept: { id: number; name: string | null } | null;
  session_question_id: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
};

export type ConversationDetail = Conversation & { messages: TutorMessage[] };

export type TutorReply = {
  conversation: Conversation;
  student_message: TutorMessage;
  reply: TutorMessage;
};

export type TutorStatus = {
  ai_available: boolean;
  reason: "not_configured" | "disabled" | "daily_limit" | "budget" | null;
  notice: string | null;
  messages_today: number;
  daily_limit: number;
  modes: { id: TutorMode; label: string }[];
};
