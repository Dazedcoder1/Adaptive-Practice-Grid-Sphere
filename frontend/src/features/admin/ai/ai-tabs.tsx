"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PageHeader } from "@/components/layout/portal-shell";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/admin/ai", label: "Overview & settings" },
  { href: "/admin/ai/documents", label: "Documents" },
  { href: "/admin/ai/retrieval", label: "Retrieval testing" },
  { href: "/admin/ai/prompts", label: "Prompts" },
  { href: "/admin/ai/usage", label: "Usage" },
];

export function AiHeader({ actions }: { actions?: React.ReactNode }) {
  const path = usePathname();
  return (
    <>
      <PageHeader
        title="AI & RAG"
        description="The tutor's provider, limits, study material and prompts. The AI never decides marks or mastery."
        actions={actions}
      />
      <nav aria-label="AI sections" className="mb-6 flex gap-1 overflow-x-auto border-b">
        {TABS.map((t) => {
          const active = t.href === "/admin/ai" ? path === t.href : path.startsWith(t.href);
          return (
            <Link
              key={t.href}
              href={t.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "-mb-px border-b-2 px-3 py-2 text-sm whitespace-nowrap transition-colors",
                active
                  ? "border-primary text-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground border-transparent",
              )}
            >
              {t.label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
