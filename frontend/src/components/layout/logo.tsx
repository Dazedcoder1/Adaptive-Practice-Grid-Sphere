import Link from "next/link";
import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "bg-brand-gradient shadow-primary/30 flex size-8 items-center justify-center rounded-lg text-white shadow-md",
        className,
      )}
      aria-hidden
    >
      <svg
        viewBox="0 0 24 24"
        className="size-4.5"
        fill="none"
        stroke="currentColor"
        strokeWidth={2.4}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M4 18 L10 6 L16 18" />
        <path d="M14 14 L20 8" />
        <circle cx="20" cy="8" r="1.4" fill="currentColor" stroke="none" />
      </svg>
    </span>
  );
}

export function Logo({
  href = "/",
  tone = "dark",
  suffix,
}: {
  href?: string;
  tone?: "dark" | "light";
  suffix?: string;
}) {
  return (
    <Link href={href} className="flex items-center gap-2.5 font-semibold tracking-tight">
      <LogoMark />
      <span className={tone === "light" ? "text-white" : "text-foreground"}>
        AdaptiveLearn <span className="text-brand-gradient">AI</span>
      </span>
      {suffix && (
        <span className="text-navy-foreground rounded-md bg-white/10 px-1.5 py-0.5 text-[10px] font-medium tracking-wider uppercase">
          {suffix}
        </span>
      )}
    </Link>
  );
}
