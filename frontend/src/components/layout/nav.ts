import {
  Activity,
  BarChart3,
  BookOpen,
  Bot,
  BrainCircuit,
  CalendarClock,
  ClipboardList,
  FileQuestion,
  FileText,
  GraduationCap,
  LayoutDashboard,
  type LucideIcon,
  NotebookPen,
  RotateCcw,
  ScrollText,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Target,
  Trophy,
  User,
  Users,
} from "lucide-react";

export type NavItem = { href: string; label: string; icon: LucideIcon; planned?: boolean };

/** Student Portal navigation (brief §13). `planned` items are labelled in the sidebar. */
export const studentNav: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/learn", label: "Learn", icon: BookOpen },
  { href: "/curriculum", label: "My Curriculum", icon: GraduationCap },
  { href: "/practice", label: "Practice", icon: Target },
  { href: "/tutor", label: "AI Tutor", icon: Bot, planned: true },
  { href: "/mock-tests", label: "Mock Tests", icon: ClipboardList, planned: true },
  { href: "/revision", label: "Revision", icon: RotateCcw },
  { href: "/weak-topics", label: "Weak Topics", icon: Activity },
  { href: "/error-notebook", label: "Error Notebook", icon: NotebookPen },
  { href: "/analytics", label: "Analytics", icon: BarChart3, planned: true },
  { href: "/achievements", label: "Achievements", icon: Trophy, planned: true },
  { href: "/profile", label: "Profile", icon: User },
];

/** Super Admin navigation (brief §13). */
export const adminNav: NavItem[] = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/users", label: "User Management", icon: Users },
  { href: "/admin/curriculum", label: "Curriculum", icon: GraduationCap },
  { href: "/admin/content", label: "Learning Content", icon: FileText, planned: true },
  { href: "/admin/questions", label: "Question Bank", icon: FileQuestion },
  { href: "/admin/exams", label: "Examinations", icon: CalendarClock, planned: true },
  { href: "/admin/ai", label: "AI & RAG", icon: BrainCircuit, planned: true },
  { href: "/admin/adaptive", label: "Adaptive Configuration", icon: SlidersHorizontal, planned: true },
  { href: "/admin/analytics", label: "Analytics", icon: BarChart3, planned: true },
  { href: "/admin/security", label: "Security", icon: ShieldCheck },
  { href: "/admin/audit-logs", label: "Audit Logs", icon: ScrollText },
  { href: "/admin/settings", label: "System Settings", icon: Settings },
];
