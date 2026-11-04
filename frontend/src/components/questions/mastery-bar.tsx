import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Level } from "@/types/learning";

export const LEVEL_LABEL: Record<Level, string> = {
  not_started: "Not started",
  weak: "Weak",
  developing: "Developing",
  proficient: "Proficient",
  mastered: "Mastered",
};

const LEVEL_VARIANT = {
  not_started: "muted",
  weak: "destructive",
  developing: "warning",
  proficient: "blue",
  mastered: "success",
} as const;

const LEVEL_COLOR: Record<Level, string> = {
  not_started: "bg-muted-foreground/30",
  weak: "bg-destructive",
  developing: "bg-warning",
  proficient: "bg-accent",
  mastered: "bg-success",
};

export function LevelBadge({ level }: { level: Level }) {
  return <Badge variant={LEVEL_VARIANT[level]}>{LEVEL_LABEL[level]}</Badge>;
}

/** Mastery estimate as a bar. Shows "—" until there's evidence. */
export function MasteryBar({ p, level, className }: { p: number | null; level: Level; className?: string }) {
  const pct = p == null ? 0 : Math.round(p * 100);
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className="bg-muted h-1.5 flex-1 overflow-hidden rounded-full"
        role="meter"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Mastery estimate"
      >
        <div className={cn("h-full rounded-full transition-all", LEVEL_COLOR[level])} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-muted-foreground w-9 text-right text-xs tabular-nums">{p == null ? "—" : `${pct}%`}</span>
    </div>
  );
}

export function formatDuration(seconds: number) {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  if (m < 60) return `${m} min`;
  return `${Math.floor(m / 60)} h ${m % 60} min`;
}
