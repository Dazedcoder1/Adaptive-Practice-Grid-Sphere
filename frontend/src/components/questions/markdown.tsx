"use client";

import "katex/dist/katex.min.css";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import { cn } from "@/lib/utils";

/**
 * Markdown with $inline$ and $$display$$ maths (KaTeX). Raw HTML in the source is not
 * rendered (react-markdown's default), so authored content can't inject scripts.
 */
export function Markdown({ children, className, inline }: { children: string; className?: string; inline?: boolean }) {
  return (
    <div
      className={cn(
        "max-w-none text-sm leading-relaxed [&_.katex-display]:my-3 [&_.katex-display]:overflow-x-auto [&_li]:my-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-2 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_strong]:font-semibold [&_ul]:list-disc [&_ul]:pl-5",
        inline && "[&_p]:my-0 [&_p]:inline",
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
