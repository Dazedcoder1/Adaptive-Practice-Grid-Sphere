"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Atom, Check, GraduationCap, Stethoscope } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { getMe } from "@/features/authentication/api";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import { learning } from "./api";

const MODES = [
  { id: "school", label: "School", hint: "Classes 6–12, board-aligned", icon: GraduationCap },
  { id: "jee", label: "JEE", hint: "JEE Main & Advanced", icon: Atom },
  { id: "neet", label: "NEET", hint: "Medical entrance", icon: Stethoscope },
] as const;

function Choice({
  selected,
  onClick,
  children,
  className,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        "bg-card relative rounded-xl border p-4 text-left transition-colors",
        selected ? "border-primary bg-primary/5 ring-primary/20 ring-2" : "hover:bg-muted/60",
        className,
      )}
    >
      {selected && (
        <span className="bg-primary absolute top-3 right-3 flex size-5 items-center justify-center rounded-full text-white">
          <Check className="size-3" aria-hidden />
        </span>
      )}
      {children}
    </button>
  );
}

export function OnboardingPage() {
  const router = useRouter();
  const options = useQuery({ queryKey: ["onboarding-options"], queryFn: learning.options });
  const [mode, setMode] = useState<string>("school");
  const [curriculumId, setCurriculumId] = useState<number | null>(null);
  const [subjects, setSubjects] = useState<number[]>([]);
  const [goals, setGoals] = useState<string[]>([]);
  const [days, setDays] = useState("5");
  const [minutes, setMinutes] = useState("30");
  const [examDate, setExamDate] = useState("");

  const save = useMutation({
    mutationFn: () =>
      learning.saveOnboarding({
        study_mode: mode,
        curriculum_id: curriculumId!,
        subject_ids: subjects,
        goals,
        target_exam_date: examDate || null,
        weekly_days: days ? Number(days) : null,
        minutes_per_day: minutes ? Number(minutes) : null,
      }),
    onSuccess: async () => {
      useAuthStore.getState().setUser(await getMe());
      toast.success("Your learning path is ready");
      router.replace("/dashboard");
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Couldn't save your choices."),
  });

  if (options.isLoading) return <LoadingState />;
  if (options.isError || !options.data) return <ErrorState onRetry={() => void options.refetch()} />;

  const boards = options.data.boards.filter((b) => b.study_mode === mode);
  const curricula = boards.flatMap((b) => b.curricula.map((c) => ({ ...c, board: b.name })));
  const curriculum = curricula.find((c) => c.id === curriculumId) ?? null;
  const toggle = <T,>(list: T[], v: T) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
  const ready = curriculum && subjects.length > 0 && goals.length > 0;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="Set up your learning path"
        description="Tell us what you're studying. You can change any of this later from your profile — there's no fixed timetable."
      />

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>1. What are you preparing for?</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3">
            {MODES.map((m) => (
              <Choice
                key={m.id}
                selected={mode === m.id}
                onClick={() => {
                  setMode(m.id);
                  setCurriculumId(null);
                  setSubjects([]);
                }}
              >
                <m.icon className="text-primary mb-2 size-5" aria-hidden />
                <p className="font-medium">{m.label}</p>
                <p className="text-muted-foreground text-xs">{m.hint}</p>
              </Choice>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>2. Board or exam, and class</CardTitle>
            <CardDescription>Your practice follows this syllabus version.</CardDescription>
          </CardHeader>
          <CardContent>
            {curricula.length === 0 ? (
              <Alert variant="info">
                <GraduationCap />
                <p>
                  Content for {MODES.find((m) => m.id === mode)?.label} isn&apos;t available yet. Choose{" "}
                  <strong>School</strong> to start with the CBSE Class 11 Physics sample.
                </p>
              </Alert>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {curricula.map((c) => (
                  <Choice
                    key={c.id}
                    selected={curriculumId === c.id}
                    onClick={() => {
                      setCurriculumId(c.id);
                      setSubjects(c.subjects.map((s) => s.id));
                    }}
                  >
                    <p className="font-medium">{c.name}</p>
                    <p className="text-muted-foreground text-xs">
                      {c.board}
                      {c.grade && ` · ${c.grade}`} · syllabus {c.version}
                    </p>
                    {c.is_sample && (
                      <Badge variant="warning" className="mt-2">
                        Sample content
                      </Badge>
                    )}
                  </Choice>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {curriculum && (
          <Card>
            <CardHeader>
              <CardTitle>3. Subjects</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {curriculum.subjects.map((s) => (
                <Choice
                  key={s.id}
                  selected={subjects.includes(s.id)}
                  onClick={() => setSubjects((l) => toggle(l, s.id))}
                  className="py-2.5 pr-10"
                >
                  <p className="text-sm font-medium">{s.name}</p>
                </Choice>
              ))}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>4. Your goals</CardTitle>
            <CardDescription>Pick any that apply.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2 sm:grid-cols-2">
            {options.data.goals.map((g) => (
              <Choice
                key={g.id}
                selected={goals.includes(g.id)}
                onClick={() => setGoals((l) => toggle(l, g.id))}
                className="py-3 pr-10"
              >
                <p className="text-sm">{g.label}</p>
              </Choice>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>5. Preferred study rhythm</CardTitle>
            <CardDescription>
              Used for reminders and revision spacing — never to lock you into a timetable.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            <FormField id="days" label="Days per week">
              <Select value={days} onChange={(e) => setDays(e.target.value)}>
                {[1, 2, 3, 4, 5, 6, 7].map((d) => (
                  <option key={d}>{d}</option>
                ))}
              </Select>
            </FormField>
            <FormField id="minutes" label="Minutes per day">
              <Select value={minutes} onChange={(e) => setMinutes(e.target.value)}>
                {[15, 20, 30, 45, 60, 90, 120].map((m) => (
                  <option key={m}>{m}</option>
                ))}
              </Select>
            </FormField>
            <FormField id="exam_date" label="Target exam date" hint="Optional">
              <Input type="date" value={examDate} onChange={(e) => setExamDate(e.target.value)} />
            </FormField>
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-3">
          {!ready && (
            <p className="text-muted-foreground text-sm">Choose a syllabus, at least one subject and one goal.</p>
          )}
          <Button variant="gradient" size="lg" disabled={!ready} loading={save.isPending} onClick={() => save.mutate()}>
            Start learning
          </Button>
        </div>
      </div>
    </div>
  );
}
