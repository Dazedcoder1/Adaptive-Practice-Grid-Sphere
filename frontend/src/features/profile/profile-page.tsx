"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Laptop, LogOut, ShieldAlert, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { ErrorState, LoadingState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/portal-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Select } from "@/components/ui/select";
import { changePassword, getMe, listSessions, logoutAll, revokeSession } from "@/features/authentication/api";
import { type ChangePasswordValues, changePasswordSchema } from "@/features/authentication/schemas";
import { formatDateTime, formatRelative } from "@/lib/utils";
import { ApiError, api } from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import type { Message, StudentProfile } from "@/types/api";

const TIMEZONES = [
  "Asia/Kolkata",
  "Asia/Dubai",
  "Asia/Singapore",
  "Asia/Kathmandu",
  "Asia/Dhaka",
  "Europe/London",
  "America/New_York",
  "UTC",
];

const profileSchema = z.object({
  display_name: z.string().trim().min(1, "Enter a name.").max(80),
  timezone: z.string().min(1),
});
type ProfileValues = z.infer<typeof profileSchema>;

const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong.");

function ProfileCard({ profile }: { profile: StudentProfile }) {
  const qc = useQueryClient();
  const form = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    values: { display_name: profile.display_name, timezone: profile.timezone },
  });
  const save = useMutation({
    mutationFn: (v: ProfileValues) => api<StudentProfile>("/students/me", { method: "PATCH", body: v }),
    onSuccess: async (p) => {
      qc.setQueryData(["profile"], p);
      useAuthStore.getState().setUser(await getMe());
      toast.success("Profile saved");
    },
    onError: (e) => toast.error(errMsg(e)),
  });
  const tzs = TIMEZONES.includes(profile.timezone) ? TIMEZONES : [profile.timezone, ...TIMEZONES];

  return (
    <Card>
      <form onSubmit={form.handleSubmit((v) => save.mutate(v))} noValidate>
        <CardHeader>
          <CardTitle>Personal profile</CardTitle>
          <CardDescription>We keep only what&apos;s needed to personalise your learning.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <FormField id="display_name" label="Name" error={form.formState.errors.display_name?.message}>
            <Input {...form.register("display_name")} />
          </FormField>
          <FormField id="timezone" label="Timezone" hint="Used for streaks and revision reminders.">
            <Select {...form.register("timezone")}>
              {tzs.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </Select>
          </FormField>
          <FormField id="email" label="Email" hint="Contact support to change your email.">
            <Input value={profile.email} disabled readOnly />
          </FormField>
          <FormField id="member" label="Member since">
            <Input value={formatDateTime(profile.created_at)} disabled readOnly />
          </FormField>
        </CardContent>
        <CardFooter className="justify-end">
          <Button type="submit" loading={save.isPending} disabled={!form.formState.isDirty}>
            Save changes
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}

function PasswordCard() {
  const qc = useQueryClient();
  const form = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });
  const { errors } = form.formState;
  const change = useMutation({
    mutationFn: (v: ChangePasswordValues) => changePassword(v.current_password, v.new_password),
    onSuccess: (r) => {
      form.reset();
      void qc.invalidateQueries({ queryKey: ["sessions"] });
      toast.success(r.message);
    },
    onError: (e) => {
      if (e instanceof ApiError && e.code === "wrong_password")
        form.setError("current_password", { message: e.message });
      else toast.error(errMsg(e));
    },
  });
  return (
    <Card>
      <form onSubmit={form.handleSubmit((v) => change.mutate(v))} noValidate>
        <CardHeader>
          <CardTitle>Password</CardTitle>
          <CardDescription>Changing it signs out your other devices.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <FormField id="current_password" label="Current password" error={errors.current_password?.message}>
            <PasswordInput autoComplete="current-password" {...form.register("current_password")} />
          </FormField>
          <FormField id="new_password" label="New password" error={errors.new_password?.message}>
            <PasswordInput autoComplete="new-password" {...form.register("new_password")} />
          </FormField>
          <FormField id="confirm_password" label="Confirm" error={errors.confirm_password?.message}>
            <PasswordInput autoComplete="new-password" {...form.register("confirm_password")} />
          </FormField>
        </CardContent>
        <CardFooter className="justify-end">
          <Button type="submit" loading={change.isPending}>
            Change password
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}

function describeAgent(ua: string | null) {
  if (!ua) return "Unknown device";
  const browser = /Edg\//.test(ua)
    ? "Edge"
    : /Chrome\//.test(ua)
      ? "Chrome"
      : /Firefox\//.test(ua)
        ? "Firefox"
        : /Safari\//.test(ua)
          ? "Safari"
          : "Browser";
  const os = /Windows/.test(ua)
    ? "Windows"
    : /Android/.test(ua)
      ? "Android"
      : /iPhone|iPad/.test(ua)
        ? "iOS"
        : /Mac OS/.test(ua)
          ? "macOS"
          : /Linux/.test(ua)
            ? "Linux"
            : "";
  return os ? `${browser} on ${os}` : browser;
}

function SessionsCard() {
  const qc = useQueryClient();
  const router = useRouter();
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: listSessions });
  const revoke = useMutation({
    mutationFn: revokeSession,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sessions"] });
      toast.success("Device signed out");
    },
    onError: (e) => toast.error(errMsg(e)),
  });
  const all = useMutation({
    mutationFn: logoutAll,
    onSuccess: () => router.replace("/login"),
    onError: (e) => toast.error(errMsg(e)),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Signed-in devices</CardTitle>
        <CardDescription>Sign out anything you don&apos;t recognise.</CardDescription>
      </CardHeader>
      <CardContent>
        {sessions.isLoading ? (
          <LoadingState />
        ) : sessions.isError ? (
          <ErrorState message={errMsg(sessions.error)} onRetry={() => void sessions.refetch()} />
        ) : (
          <ul className="divide-y">
            {sessions.data?.map((s) => (
              <li key={s.id} className="flex items-center gap-3 py-3">
                <Laptop className="text-muted-foreground size-5" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2 text-sm font-medium">
                    {describeAgent(s.user_agent)} {s.current && <Badge variant="success">This device</Badge>}
                  </p>
                  <p className="text-muted-foreground text-xs">
                    Signed in {formatRelative(s.created_at)}
                    {s.ip_address && ` · ${s.ip_address}`}
                  </p>
                </div>
                {!s.current && (
                  <Button
                    variant="ghost"
                    size="sm"
                    loading={revoke.isPending && revoke.variables === s.id}
                    onClick={() => revoke.mutate(s.id)}
                  >
                    Sign out
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
      <CardFooter className="justify-end">
        <Button variant="outline" loading={all.isPending} onClick={() => all.mutate()}>
          <LogOut /> Sign out everywhere
        </Button>
      </CardFooter>
    </Card>
  );
}

function PrivacyCard({ profile }: { profile: StudentProfile }) {
  const qc = useQueryClient();
  const req = useMutation({
    mutationFn: (cancel: boolean) =>
      api<Message & { deletion_requested_at: string | null }>("/students/me/deletion-request", {
        method: cancel ? "DELETE" : "POST",
      }),
    onSuccess: (r) => {
      qc.setQueryData<StudentProfile>(["profile"], (p) =>
        p ? { ...p, deletion_requested_at: r.deletion_requested_at } : p,
      );
      toast.success(r.message);
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Privacy & account</CardTitle>
        <CardDescription>
          {profile.is_minor
            ? `Your account was approved by your parent or guardian${profile.guardian_email ? ` (${profile.guardian_email})` : ""}.`
            : "You can ask us to delete your account and personal data at any time."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {profile.deletion_requested_at ? (
          <div className="border-warning/30 bg-warning/5 flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center">
            <ShieldAlert className="text-warning size-5" aria-hidden />
            <p className="flex-1 text-sm">
              Deletion requested on {formatDateTime(profile.deletion_requested_at)}. An administrator will process it.
            </p>
            <Button variant="outline" size="sm" loading={req.isPending} onClick={() => req.mutate(true)}>
              Cancel request
            </Button>
          </div>
        ) : (
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline" className="text-destructive">
                <Trash2 /> Request account deletion
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Delete your account?</DialogTitle>
                <DialogDescription>
                  An administrator will remove your personal data. Your learning progress can&apos;t be recovered
                  afterwards. You can cancel until the request is processed.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <DialogClose asChild>
                  <Button variant="outline">Keep my account</Button>
                </DialogClose>
                <DialogClose asChild>
                  <Button variant="destructive" onClick={() => req.mutate(false)}>
                    Request deletion
                  </Button>
                </DialogClose>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
        <p className="text-muted-foreground mt-4 text-xs">
          Academic preferences, study goals and notification settings will appear here with onboarding (Phase 1).
        </p>
      </CardContent>
    </Card>
  );
}

export function ProfilePage() {
  const profile = useQuery({ queryKey: ["profile"], queryFn: () => api<StudentProfile>("/students/me") });
  return (
    <>
      <PageHeader title="Profile & settings" description="Manage your details, security and privacy." />
      {profile.isLoading ? (
        <LoadingState />
      ) : profile.isError || !profile.data ? (
        <ErrorState message={errMsg(profile.error)} onRetry={() => void profile.refetch()} />
      ) : (
        <div className="space-y-6">
          <ProfileCard profile={profile.data} />
          <PasswordCard />
          <SessionsCard />
          <PrivacyCard profile={profile.data} />
        </div>
      )}
    </>
  );
}
