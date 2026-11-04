import { CheckCircle2 } from "lucide-react";
import { Logo } from "./logo";

/** Two-column auth layout: form on the left, value proposition on the right (desktop). */
export function AuthShell({
  title,
  subtitle,
  children,
  aside = "student",
}: {
  title: string;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
  aside?: "student" | "admin";
}) {
  const points =
    aside === "admin"
      ? [
          "Curriculum, content and question bank control",
          "Approval workflow before anything reaches students",
          "Full audit trail of administrative actions",
        ]
      : [
          "A learning path that adapts to what you already know",
          "Practice that targets your weak concepts",
          "Revision scheduled from your own learning evidence",
        ];
  return (
    <div className="grid min-h-screen lg:grid-cols-[1fr_minmax(0,32rem)]">
      <main className="bg-soft-gradient flex flex-col px-6 py-8 sm:px-12">
        <Logo />
        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="text-muted-foreground mt-1.5 text-sm">{subtitle}</p>}
          <div className="mt-8">{children}</div>
        </div>
      </main>
      <aside className="bg-navy relative hidden overflow-hidden p-12 text-white lg:flex lg:flex-col lg:justify-end">
        <div className="bg-primary/40 absolute -top-24 -right-24 size-96 rounded-full blur-3xl" aria-hidden />
        <div className="bg-accent/30 absolute -bottom-32 -left-16 size-96 rounded-full blur-3xl" aria-hidden />
        <div className="relative">
          <p className="text-navy-foreground text-sm font-medium tracking-widest uppercase">
            {aside === "admin" ? "Super Admin Portal" : "For Classes 6–12 · JEE · NEET"}
          </p>
          <p className="mt-3 text-3xl leading-tight font-semibold">
            {aside === "admin" ? "Run the platform with confidence." : "Learn at your own pace, on your own path."}
          </p>
          <ul className="text-navy-foreground mt-8 space-y-3 text-sm">
            {points.map((p) => (
              <li key={p} className="flex gap-2.5">
                <CheckCircle2 className="text-primary mt-0.5 size-4 shrink-0" aria-hidden />
                {p}
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  );
}
