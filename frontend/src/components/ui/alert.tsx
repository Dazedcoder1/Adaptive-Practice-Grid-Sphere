import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const alertVariants = cva("flex gap-3 rounded-lg border p-3.5 text-sm [&_svg]:mt-0.5 [&_svg]:size-4 [&_svg]:shrink-0", {
  variants: {
    variant: {
      info: "border-accent/25 bg-accent/5 text-foreground [&_svg]:text-accent",
      success: "border-success/25 bg-success/5 [&_svg]:text-success",
      warning: "border-warning/30 bg-warning/5 [&_svg]:text-warning",
      destructive: "border-destructive/25 bg-destructive/5 [&_svg]:text-destructive",
    },
  },
  defaultVariants: { variant: "info" },
});

export function Alert({
  className,
  variant,
  ...props
}: React.ComponentProps<"div"> & VariantProps<typeof alertVariants>) {
  return <div role="alert" className={cn(alertVariants({ variant }), className)} {...props} />;
}
