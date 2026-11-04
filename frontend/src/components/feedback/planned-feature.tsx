import { Clock, type LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

/** Honest placeholder for a module that isn't built yet (brief §4: no functionally empty UI). */
export function PlannedFeature({
  icon: Icon,
  title,
  phase,
  description,
  capabilities,
}: {
  icon: LucideIcon;
  title: string;
  phase: string;
  description: string;
  capabilities: string[];
}) {
  return (
    <Card className="overflow-hidden">
      <div className="bg-soft-gradient flex flex-col items-start gap-4 p-8 sm:flex-row sm:items-center">
        <div className="bg-brand-gradient shadow-primary/25 flex size-14 shrink-0 items-center justify-center rounded-2xl text-white shadow-lg">
          <Icon className="size-7" aria-hidden />
        </div>
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-semibold">{title}</h2>
            <Badge variant="warning">
              <Clock className="size-3" aria-hidden /> Planned · {phase}
            </Badge>
          </div>
          <p className="text-muted-foreground mt-1 max-w-2xl text-sm">{description}</p>
        </div>
      </div>
      <div className="border-t p-6">
        <p className="text-muted-foreground mb-3 text-xs font-medium tracking-wide uppercase">What this will include</p>
        <ul className="grid gap-2 text-sm sm:grid-cols-2">
          {capabilities.map((c) => (
            <li key={c} className="flex items-start gap-2">
              <span className="bg-primary/60 mt-1.5 size-1.5 shrink-0 rounded-full" aria-hidden />
              {c}
            </li>
          ))}
        </ul>
        <p className="text-muted-foreground mt-5 text-xs">
          Not available yet — nothing on this page is simulated or uses demo data.
        </p>
      </div>
    </Card>
  );
}
