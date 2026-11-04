import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  icon: Icon,
  hint,
  tone = "default",
}: {
  label: string;
  value: React.ReactNode;
  icon: LucideIcon;
  hint?: React.ReactNode;
  tone?: "default" | "warning" | "danger";
}) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-muted-foreground text-sm">{label}</p>
          <p className="mt-1.5 text-3xl font-semibold tracking-tight tabular-nums">{value}</p>
        </div>
        <span
          className={cn(
            "flex size-10 items-center justify-center rounded-xl",
            tone === "danger"
              ? "bg-destructive/10 text-destructive"
              : tone === "warning"
                ? "bg-warning/10 text-warning"
                : "bg-primary/10 text-primary",
          )}
        >
          <Icon className="size-5" aria-hidden />
        </span>
      </div>
      {hint && <p className="text-muted-foreground mt-3 text-xs">{hint}</p>}
    </Card>
  );
}
