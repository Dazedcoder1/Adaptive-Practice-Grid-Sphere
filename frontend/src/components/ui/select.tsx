import * as React from "react";
import { cn } from "@/lib/utils";

/** Native select styled to match Input — accessible and keyboard-friendly by default. */
export function Select({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "border-input bg-card focus-visible:border-ring focus-visible:ring-ring/20 h-10 rounded-lg border px-3 text-sm shadow-xs focus-visible:ring-3 focus-visible:outline-none",
        className,
      )}
      {...props}
    />
  );
}
