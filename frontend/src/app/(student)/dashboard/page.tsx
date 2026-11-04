"use client";

import { ArrowRight, BookOpen, CircleCheck, Clock, Flame, Gauge, Target } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/layout/portal-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/stores/auth";

const metrics = [
  { label: "Concept mastery", icon: Gauge },
  { label: "Questions attempted", icon: Target },
  { label: "Accuracy", icon: CircleCheck },
  { label: "Study time", icon: Clock },
  { label: "Learning streak", icon: Flame },
];

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const first = user?.display_name?.split(" ")[0] ?? "there";

  return (
    <>
      <PageHeader title={`${greeting()}, ${first}`} description="Your learning journey starts here." />

      <Card className="mb-6 overflow-hidden">
        <div className="bg-soft-gradient flex flex-col gap-4 p-6 sm:flex-row sm:items-center">
          <div className="bg-brand-gradient flex size-12 shrink-0 items-center justify-center rounded-2xl text-white">
            <BookOpen className="size-6" aria-hidden />
          </div>
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="font-semibold">Set up your learning path</h2>
              <Badge variant="warning">Coming in Phase 1</Badge>
            </div>
            <p className="text-muted-foreground mt-1 text-sm">
              Onboarding will ask for your study mode (School, JEE or NEET), board or exam, class, subjects and goals —
              then build a path from a short diagnostic.
            </p>
          </div>
          <Button asChild variant="outline">
            <Link href="/profile">
              Review your profile <ArrowRight />
            </Link>
          </Button>
        </div>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {metrics.map(({ label, icon: Icon }) => (
          <Card key={label}>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2">
                <Icon className="size-4" aria-hidden /> {label}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground/60 text-2xl font-semibold">—</p>
              <p className="text-muted-foreground mt-1 text-xs">No activity yet</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        {[
          ["Recommended next activity", "Recommendations come from your knowledge model once you start practising."],
          ["Weak topics", "Concepts where your mastery is low will be listed here."],
          ["Upcoming revision", "Spaced-repetition reviews will be scheduled from your own answers."],
        ].map(([title, body]) => (
          <Card key={title}>
            <CardHeader>
              <CardTitle>{title}</CardTitle>
              <CardDescription>{body}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>
      <p className="text-muted-foreground mt-6 text-xs">
        Every figure on this dashboard will be calculated from your real activity. Nothing is shown until there is data.
      </p>
    </>
  );
}
