import * as React from "react";
import { cn } from "@/lib/utils";
import { Label } from "./label";

/** Label + control + hint/error, wired for screen readers. */
export function FormField({
  id,
  label,
  error,
  hint,
  className,
  children,
}: {
  id: string;
  label: React.ReactNode;
  error?: string;
  hint?: React.ReactNode;
  className?: string;
  children: React.ReactElement<{ id?: string; "aria-invalid"?: boolean; "aria-describedby"?: string }>;
}) {
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <Label htmlFor={id}>{label}</Label>
      {React.cloneElement(children, { id, "aria-invalid": !!error, "aria-describedby": describedBy })}
      {error ? (
        <p id={`${id}-error`} className="text-destructive text-xs">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-muted-foreground text-xs">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
