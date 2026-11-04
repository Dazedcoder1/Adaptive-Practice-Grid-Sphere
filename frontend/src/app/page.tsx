import {
  ArrowRight,
  Atom,
  BarChart3,
  Bot,
  BrainCircuit,
  ClipboardList,
  FlaskConical,
  GraduationCap,
  NotebookPen,
  RotateCcw,
  Route,
  ShieldCheck,
  Stethoscope,
  Target,
} from "lucide-react";
import Link from "next/link";
import { Logo } from "@/components/layout/logo";
import { Button } from "@/components/ui/button";
import { LandingNav } from "@/features/landing/landing-nav";
import { Reveal } from "@/features/landing/reveal";

const steps = [
  {
    icon: Target,
    title: "Find your starting point",
    body: "A short diagnostic estimates what you already know, concept by concept.",
  },
  {
    icon: Route,
    title: "Get your own path",
    body: "Your knowledge model recommends what to learn next — prerequisites first.",
  },
  {
    icon: BrainCircuit,
    title: "Practise adaptively",
    body: "Each question is chosen for you, and difficulty rises as your mastery does.",
  },
  {
    icon: RotateCcw,
    title: "Remember it",
    body: "Spaced revision brings back concepts just before you'd forget them.",
  },
];

const paths = [
  {
    icon: GraduationCap,
    title: "School",
    tag: "Classes 6–12",
    body: "Board-aligned subjects, chapters and concepts, with explanations and worked examples.",
  },
  {
    icon: Atom,
    title: "JEE",
    tag: "Main & Advanced",
    body: "Physics, Chemistry and Mathematics with difficulty that climbs to Advanced level.",
  },
  {
    icon: Stethoscope,
    title: "NEET",
    tag: "Medical entrance",
    body: "Physics, Chemistry and Biology practice tuned to the NEET pattern.",
  },
];

const features = [
  {
    icon: BrainCircuit,
    title: "Knowledge tracing",
    body: "Concept mastery is estimated with Bayesian Knowledge Tracing — transparent and versioned.",
  },
  {
    icon: Target,
    title: "Adaptive practice",
    body: "8 question types, instant feedback and hints, with marks always calculated on the server.",
  },
  {
    icon: ClipboardList,
    title: "Mock examinations",
    body: "Fixed, standardised tests with server timers and negative marking — separate from practice.",
  },
  {
    icon: NotebookPen,
    title: "Error notebook",
    body: "Every mistake is saved so you can review the explanation and try again.",
  },
  {
    icon: BarChart3,
    title: "Honest analytics",
    body: "Progress from your real activity. Readiness is only claimed with clearly stated criteria.",
  },
  {
    icon: Bot,
    title: "AI Tutor",
    body: "Coming next: a tutor that guides your reasoning — it never decides your marks or mastery.",
  },
];

async function CopyrightYear() {
  "use cache"; // computed when the page is prerendered, not on every request
  return <>{new Date().getFullYear()}</>;
}

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <LandingNav />

      <section className="bg-soft-gradient relative overflow-hidden">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:py-28">
          <Reveal>
            <p className="bg-card text-muted-foreground inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium shadow-sm">
              <FlaskConical className="text-primary size-3.5" aria-hidden /> Self-paced · Adaptive · For Classes 6–12,
              JEE & NEET
            </p>
            <h1 className="mt-6 text-4xl leading-[1.1] font-semibold tracking-tight sm:text-5xl">
              Every student gets their <span className="text-brand-gradient">own learning journey.</span>
            </h1>
            <p className="text-muted-foreground mt-5 max-w-lg text-lg">
              AdaptiveLearn AI works out what you know, finds your weak concepts and picks the next best thing to learn
              or practise — so you can make progress on your own, at your own pace.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg" variant="gradient">
                <Link href="/register">
                  Create free account <ArrowRight />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/login">Sign in</Link>
              </Button>
            </div>
          </Reveal>

          <Reveal delay={0.1} className="relative">
            <div className="bg-brand-gradient absolute -inset-6 rounded-[2rem] opacity-15 blur-2xl" aria-hidden />
            <div className="bg-card relative rounded-2xl border p-6 shadow-xl">
              <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                How your next question is chosen
              </p>
              <ol className="mt-4 space-y-3">
                {[
                  ["Your mastery of each concept", "from your own answers"],
                  ["Prerequisites you still need", "fill gaps before moving on"],
                  ["The right difficulty", "challenging, but within reach"],
                  ["Variety", "no endless loop on one weak spot"],
                ].map(([a, b], i) => (
                  <li key={a} className="bg-muted/60 flex items-start gap-3 rounded-xl p-3">
                    <span className="bg-brand-gradient flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white">
                      {i + 1}
                    </span>
                    <span className="text-sm">
                      <span className="font-medium">{a}</span>
                      <span className="text-muted-foreground"> — {b}</span>
                    </span>
                  </li>
                ))}
              </ol>
              <p className="text-muted-foreground mt-4 flex items-center gap-2 text-xs">
                <ShieldCheck className="text-success size-4" aria-hidden /> Answers are evaluated on our servers, never
                in your browser.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      <section id="how-it-works" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-20 sm:px-6">
        <Reveal>
          <h2 className="text-3xl font-semibold tracking-tight">How adaptive learning works</h2>
          <p className="text-muted-foreground mt-2 max-w-2xl">
            No fixed timetable. The platform responds to what you actually know.
          </p>
        </Reveal>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((s, i) => (
            <Reveal key={s.title} delay={i * 0.06}>
              <div className="bg-card h-full rounded-xl border p-5 shadow-sm">
                <div className="bg-primary/10 text-primary flex size-10 items-center justify-center rounded-xl">
                  <s.icon className="size-5" aria-hidden />
                </div>
                <p className="text-muted-foreground mt-4 text-xs font-medium">Step {i + 1}</p>
                <h3 className="mt-1 font-semibold">{s.title}</h3>
                <p className="text-muted-foreground mt-1.5 text-sm">{s.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="paths" className="bg-navy scroll-mt-20 py-20 text-white">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Reveal>
            <h2 className="text-3xl font-semibold tracking-tight">Choose your path</h2>
            <p className="text-navy-foreground mt-2">Switch or add study modes any time from your profile.</p>
          </Reveal>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {paths.map((p, i) => (
              <Reveal key={p.title} delay={i * 0.06}>
                <div className="bg-navy-2 h-full rounded-xl border border-white/10 p-6">
                  <div className="flex items-center justify-between">
                    <span className="bg-brand-gradient flex size-11 items-center justify-center rounded-xl">
                      <p.icon className="size-5" aria-hidden />
                    </span>
                    <span className="text-navy-foreground rounded-full bg-white/10 px-2.5 py-0.5 text-xs">{p.tag}</span>
                  </div>
                  <h3 className="mt-5 text-xl font-semibold">{p.title}</h3>
                  <p className="text-navy-foreground mt-2 text-sm">{p.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section id="features" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-20 sm:px-6">
        <Reveal>
          <h2 className="text-3xl font-semibold tracking-tight">Built for real learning</h2>
          <p className="text-muted-foreground mt-2 max-w-2xl">
            Designed around evidence of what you know — not engagement for its own sake.
          </p>
        </Reveal>
        <div className="mt-10 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <Reveal key={f.title} delay={i * 0.04}>
              <f.icon className="text-primary size-6" aria-hidden />
              <h3 className="mt-3 font-semibold">{f.title}</h3>
              <p className="text-muted-foreground mt-1.5 text-sm">{f.body}</p>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
        <Reveal>
          <div className="bg-brand-gradient relative overflow-hidden rounded-2xl px-8 py-12 text-white sm:px-12">
            <h2 className="max-w-xl text-3xl font-semibold tracking-tight">Start where you are. Go at your pace.</h2>
            <p className="mt-2 max-w-xl text-white/80">
              Free to start. Students under 18 need a parent or guardian&apos;s consent.
            </p>
            <Button asChild size="lg" className="text-primary mt-6 bg-white hover:bg-white/90">
              <Link href="/register">
                Create your account <ArrowRight />
              </Link>
            </Button>
          </div>
        </Reveal>
      </section>

      <footer className="bg-card border-t">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <Logo />
            <p className="text-muted-foreground mt-2 text-sm">Adaptive learning for Classes 6–12, JEE and NEET.</p>
          </div>
          <nav className="text-muted-foreground flex flex-wrap gap-x-6 gap-y-2 text-sm" aria-label="Footer">
            <a href="#how-it-works" className="hover:text-foreground">
              How it works
            </a>
            <a href="#features" className="hover:text-foreground">
              Features
            </a>
            <Link href="/login" className="hover:text-foreground">
              Student sign in
            </Link>
            <Link href="/admin/login" className="hover:text-foreground">
              Admin
            </Link>
          </nav>
        </div>
        <p className="text-muted-foreground border-t py-4 text-center text-xs">
          © <CopyrightYear /> AdaptiveLearn AI
        </p>
      </footer>
    </div>
  );
}
