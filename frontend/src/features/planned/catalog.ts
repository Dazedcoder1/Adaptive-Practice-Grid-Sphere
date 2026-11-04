import {
  BarChart3,
  Bot,
  BrainCircuit,
  CalendarClock,
  ClipboardList,
  FileText,
  SlidersHorizontal,
  Trophy,
  type LucideIcon,
} from "lucide-react";

type Entry = { title: string; icon: LucideIcon; phase: string; description: string; capabilities: string[] };

export const studentPlanned: Record<string, Entry> = {
  tutor: {
    title: "AI Tutor",
    icon: Bot,
    phase: "Phase 2",
    description: "A tutor that guides your reasoning instead of handing you answers.",
    capabilities: [
      "Teach me \u00b7 Give a hint \u00b7 Solve with me",
      "Test me \u00b7 Find my mistake",
      "Answers grounded in approved learning material, with citations",
      "Never decides your marks or mastery",
    ],
  },
  "mock-tests": {
    title: "Mock Tests",
    icon: ClipboardList,
    phase: "Phase 1",
    description: "Standardised exams with fixed question sets \u2014 kept separate from adaptive practice.",
    capabilities: [
      "JEE/NEET-style patterns with sections",
      "Server-side timers and answer saving",
      "Negative marking and fixed scoring",
      "Detailed result reports",
      "Previous test history",
    ],
  },
  analytics: {
    title: "Performance Analytics",
    icon: BarChart3,
    phase: "Phase 1",
    description: "How you're actually progressing \u2014 calculated, never estimated for show.",
    capabilities: [
      "Accuracy, mastery and practice time",
      "Subject- and chapter-wise performance",
      "Trends and improvement over time",
      "Exam-readiness indicators with stated criteria",
    ],
  },
  achievements: {
    title: "Achievements",
    icon: Trophy,
    phase: "Phase 1",
    description: "Rewards for real learning milestones, never duplicated by retries.",
    capabilities: ["XP ledger", "Learning streaks", "Achievements and milestones", "Optional leaderboards"],
  },
};

export const adminPlanned: Record<string, Entry> = {
  content: {
    title: "Learning Content",
    icon: FileText,
    phase: "Phase 1",
    description: "Lessons, explanations, examples and diagrams mapped to concepts.",
    capabilities: [
      "Create lessons and upload documents",
      "Worked examples and diagrams (stored in R2)",
      "Map content to concepts",
      "Edit with version history",
      "Publish and archive",
    ],
  },
  exams: {
    title: "Examinations",
    icon: CalendarClock,
    phase: "Phase 1",
    description: "Exam patterns, marking schemes and mock tests.",
    capabilities: [
      "Exam patterns and sections",
      "Marking schemes and negative marking",
      "Durations and fixed question sets",
      "Publish mock exams",
    ],
  },
  ai: {
    title: "AI & RAG",
    icon: BrainCircuit,
    phase: "Phase 2",
    description: "Provider-independent AI configuration and retrieval management.",
    capabilities: [
      "Provider and model selection",
      "API keys via secret storage",
      "Document ingestion and chunking",
      "Retrieval evaluation and prompt versions",
      "Usage, cost limits and fallbacks",
    ],
  },
  adaptive: {
    title: "Adaptive Configuration",
    icon: SlidersHorizontal,
    phase: "Phase 1",
    description: "Controlled, versioned configuration of the adaptive engine.",
    capabilities: [
      "BKT parameters and mastery thresholds",
      "Difficulty levels and selection rules",
      "Exploration settings",
      "Model versioning \u2014 never rewrites history",
    ],
  },
  analytics: {
    title: "Platform Analytics",
    icon: BarChart3,
    phase: "Phase 1",
    description: "Learning and engagement analytics from pre-aggregated data.",
    capabilities: [
      "Practice and attempt volumes",
      "Curriculum coverage",
      "Content approval backlog",
      "Cohort learning trends",
    ],
  },
};
