import * as React from "react";
import { cn } from "@/lib/utils";

export function Table({ className, ...props }: React.ComponentProps<"table">) {
  return (
    <div className="w-full overflow-x-auto">
      <table className={cn("w-full caption-bottom text-sm", className)} {...props} />
    </div>
  );
}
export function TableHeader(props: React.ComponentProps<"thead">) {
  return <thead {...props} className={cn("[&_tr]:border-b", props.className)} />;
}
export function TableBody(props: React.ComponentProps<"tbody">) {
  return <tbody {...props} className={cn("[&_tr:last-child]:border-0", props.className)} />;
}
export function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return <tr className={cn("hover:bg-muted/50 border-b transition-colors", className)} {...props} />;
}
export function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return (
    <th
      className={cn(
        "text-muted-foreground h-10 px-3 text-left align-middle text-xs font-medium tracking-wide uppercase",
        className,
      )}
      {...props}
    />
  );
}
export function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return <td className={cn("px-3 py-3 align-middle", className)} {...props} />;
}
