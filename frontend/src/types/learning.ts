export type Level = "not_started" | "weak" | "developing" | "proficient" | "mastered";

export type Mastery = {
  p_known: number | null;
  level: Level;
  attempts: number;
  correct: number;
  confidence: number;
  last_practiced_at: string | null;
};

export type ConceptRef = {
  id: number;
  code: string;
  name: string;
  topic: { id: number; name: string };
  chapter: { id: number; name: string };
  subject: { id: number; name: string };
  curriculum_id: number;
};

export type TreeConcept = Mastery & {
  id: number;
  code: string;
  name: string;
  sequence: number;
  prerequisite_ids: number[];
  question_count: number;
  description?: string;
};
export type TreeTopic = { id: number; name: string; sequence: number; concepts: TreeConcept[] };
export type TreeChapter = {
  id: number;
  name: string;
  sequence: number;
  topics: TreeTopic[];
  concept_count?: number;
  completed_count?: number;
  practisable?: boolean;
};
export type TreeSubject = { id: number; code: string; name: string; sequence: number; chapters: TreeChapter[] };
export type CurriculumTree = {
  id: number;
  name: string;
  version: string;
  status: string;
  is_sample: boolean;
  board: { id: number; name: string; code: string };
  grade: { id: number; name: string } | null;
  subjects: TreeSubject[];
};

export type ConceptDetail = ConceptRef &
  Mastery & {
    description: string;
    prerequisites: (ConceptRef & Mastery)[];
    unlocks: (ConceptRef & Mastery)[];
    question_count: number;
  };

export type OnboardingOptions = {
  boards: {
    id: number;
    code: string;
    name: string;
    kind: "board" | "exam";
    study_mode: "school" | "jee" | "neet";
    curricula: {
      id: number;
      name: string;
      version: string;
      is_sample: boolean;
      grade: string | null;
      subjects: { id: number; name: string; code: string }[];
    }[];
  }[];
  goals: { id: string; label: string }[];
};

export type QuestionType =
  | "mcq_single"
  | "mcq_multi"
  | "numerical"
  | "integer"
  | "fill_blank"
  | "match"
  | "assertion_reason"
  | "subjective"
  | "diagram";

export type Option = { id: string; text: string };

export type QuestionContent = {
  options?: Option[];
  unit?: string;
  blanks?: number;
  left?: Option[];
  right?: Option[];
  image?: string;
  image_alt?: string;
  assertion?: string;
  reason?: string;
};

export type StudentQuestion = {
  version_id: string;
  question_id: string;
  type: QuestionType;
  difficulty: number;
  stem: string;
  content: QuestionContent;
  estimated_seconds: number;
  hints_available: number;
  hints: string[];
  concepts: { id: number; name: string }[];
};

export type Response = {
  selected?: string | string[];
  value?: string;
  values?: string[];
  pairs?: Record<string, string>;
  text?: string;
};

export type SessionMode = "adaptive" | "diagnostic" | "topic" | "revision" | "review";

export type SessionSummary = {
  id: string;
  mode: SessionMode;
  status: "active" | "paused" | "completed";
  title: string;
  target_count: number;
  answered_count: number;
  correct_count: number;
  active_seconds: number;
  created_at: string;
  completed_at: string | null;
  last_activity_at: string;
};

export type Delivery =
  | { finished: true; session: SessionSummary; exhausted?: boolean }
  | {
      finished: false;
      session: SessionSummary;
      session_question_id: string;
      position: number;
      question: StudentQuestion;
      why: string;
      delivered_at: string;
    };

export type CorrectAnswer = {
  correct?: string | string[];
  value?: number;
  unit?: string | null;
  accepted?: string[];
  pairs?: Record<string, string>;
  model_answer?: string;
};

export type Feedback = {
  attempt_id: string;
  evaluation: "correct" | "partial" | "incorrect" | "ungraded";
  score: number;
  correct_answer: CorrectAnswer;
  solution: string;
  time_taken_seconds: number;
  mastery_changes: { concept_id: number; name: string; before: number; after: number }[];
  mastery_pending: boolean;
  session: SessionSummary;
};

export type SessionReport = {
  session: SessionSummary;
  accuracy: number | null;
  questions: {
    position: number;
    stem: string;
    type: QuestionType;
    difficulty: number;
    evaluation: Feedback["evaluation"];
    score: number;
    time_taken_seconds: number;
    hints_used: number;
    question_id: string;
    concept: string | null;
  }[];
  concepts: { concept_id: number; name: string; before: number; after: number; answered: number; level: Level }[];
  weak_concepts: { concept_id: number; name: string; before: number; after: number; level: Level }[];
  model_version: string;
};

export type Recommendation = {
  type: "continue_session" | "onboarding" | "diagnostic" | "revision" | "practice_concept";
  title: string;
  reason: string;
  session_id?: string;
  concept_id?: number;
  chapter_id?: number;
};

export type WeakConcept = ConceptRef & Mastery & { weak_prerequisites: ConceptRef[] };

export type RevisionItem = {
  concept_id: number;
  concept: ConceptRef | null;
  due_at: string;
  interval_days: number;
  reason: "mistake" | "review" | string;
  repetitions: number;
  lapses: number;
  last_reviewed_at: string | null;
  retention_estimate: number | null;
  mastery: Mastery;
};

export type Dashboard = {
  has_activity: boolean;
  questions_attempted: number;
  accuracy: number | null;
  study_seconds: number;
  streak_days: number;
  active_today: boolean;
  concepts_total: number;
  concepts_practised: number;
  concepts_mastered: number;
  average_mastery: number | null;
  revision_due: number;
  revision_upcoming: RevisionItem[];
  weak_concepts: WeakConcept[];
  recommendations: Recommendation[];
  recent_sessions: SessionSummary[];
  model_version: string;
};

export type MistakeCategory = "uncategorised" | "concept" | "calculation" | "misread" | "time" | "guess";

export type NotebookEntry = {
  id: string;
  question_id: string;
  source: "mistake" | "saved";
  category: MistakeCategory;
  note: string | null;
  status: "open" | "resolved";
  times_wrong: number;
  times_right_since: number;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  question: Omit<StudentQuestion, "question_id" | "concepts"> & { concepts: ConceptRef[] };
  your_answer: Response | null;
  last_evaluation: Feedback["evaluation"] | null;
  correct_answer: CorrectAnswer;
  solution: string;
  can_reattempt: boolean;
};
