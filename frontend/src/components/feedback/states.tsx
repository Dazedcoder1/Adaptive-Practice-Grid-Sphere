import { AlertTriangle, Inbox, Loader2, type LucideIcon } from "lucide-react";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function LoadingState({ label = "Loading…", className }: { label?: string; className?: string }) {
  return (
    <div
      className={cn("text-muted-foreground flex items-center justify-center gap-2 py-12 text-sm", className)}
      role="status"
    >
      <Loader2 className="size-4 animate-spin" aria-hidden />
      {label}
    </div>
  );
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: {
  icon?: LucideIcon;
  title: string;
  description?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-2 px-6 py-12 text-center", className)}>
      <div className="bg-muted mb-1 flex size-11 items-center justify-center rounded-full">
        <Icon className="text-muted-foreground size-5" aria-hidden />
      </div>
      <p className="font-medium">{title}</p>
      {description && <p className="text-muted-foreground max-w-sm text-sm">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
  className,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-2 px-6 py-12 text-center", className)}
      role="alert"
    >
      <div className="bg-destructive/10 mb-1 flex size-11 items-center justify-center rounded-full">
        <AlertTriangle className="text-destructive size-5" aria-hidden />
      </div>
      <p className="font-medium">{title}</p>
      {message && <p className="text-muted-foreground max-w-sm text-sm">{message}</p>}
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-2" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
