import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function formatRelative(value: string | null | undefined) {
  if (!value) return "Never";
  const diff = (Date.now() - new Date(value).getTime()) / 1000;
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (diff < 60) return "just now";
  if (diff < 3600) return rtf.format(-Math.round(diff / 60), "minute");
  if (diff < 86400) return rtf.format(-Math.round(diff / 3600), "hour");
  return rtf.format(-Math.round(diff / 86400), "day");
}

/** "due now", "due in 5 h", "due tomorrow", "due in 4 days". */
export function formatDue(value: string) {
  const hours = (new Date(value).getTime() - Date.now()) / 3_600_000;
  if (hours <= 0) return "due now";
  if (hours < 20) return `due in ${Math.max(1, Math.round(hours))} h`;
  const days = Math.round(hours / 24);
  return days <= 1 ? "due tomorrow" : `due in ${days} days`;
}

/** Display maths → inline maths, for short previews of Markdown passages. */
export const inlineMaths = (t: string) => t.replace(/\$\$([\s\S]+?)\$\$/g, (_, m: string) => `$${m}$`);
