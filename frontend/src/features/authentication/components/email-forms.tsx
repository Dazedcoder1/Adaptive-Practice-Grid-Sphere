"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2, Loader2, MailCheck } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { ApiError } from "@/services/api";
import { forgotPassword, grantGuardianConsent, resetPassword, verifyEmail } from "../api";
import { type EmailOnlyValues, emailOnlySchema, type ResetPasswordValues, resetPasswordSchema } from "../schemas";

export function ForgotPasswordForm() {
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<EmailOnlyValues>({ resolver: zodResolver(emailOnlySchema), defaultValues: { email: "" } });

  async function onSubmit(v: EmailOnlyValues) {
    setError(null);
    try {
      setSent((await forgotPassword(v.email)).message);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong.");
    }
  }

  if (sent) {
    return (
      <Alert variant="success">
        <MailCheck /> {sent}
      </Alert>
    );
  }
  return (
    <form method="post" onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {error && (
        <Alert variant="destructive">
          <AlertCircle /> {error}
        </Alert>
      )}
      <FormField id="email" label="Email" error={form.formState.errors.email?.message}>
        <Input type="email" autoComplete="email" autoFocus {...form.register("email")} />
      </FormField>
      <Button type="submit" variant="gradient" className="w-full" size="lg" loading={form.formState.isSubmitting}>
        Send reset link
      </Button>
    </form>
  );
}

export function ResetPasswordForm() {
  const token = useSearchParams().get("token") ?? "";
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const form = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { new_password: "", confirm_password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  if (!token) return <MissingToken />;

  async function onSubmit(v: ResetPasswordValues) {
    setError(null);
    try {
      await resetPassword(token, v.new_password);
      router.replace("/login?reset=1");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong.");
    }
  }

  return (
    <form method="post" onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {error && (
        <Alert variant="destructive">
          <AlertCircle /> {error}
        </Alert>
      )}
      <FormField
        id="new_password"
        label="New password"
        error={errors.new_password?.message}
        hint="10+ characters, letters and numbers."
      >
        <PasswordInput autoComplete="new-password" autoFocus {...form.register("new_password")} />
      </FormField>
      <FormField id="confirm_password" label="Confirm new password" error={errors.confirm_password?.message}>
        <PasswordInput autoComplete="new-password" {...form.register("confirm_password")} />
      </FormField>
      <p className="text-muted-foreground text-xs">You&apos;ll be signed out on every device.</p>
      <Button type="submit" variant="gradient" className="w-full" size="lg" loading={isSubmitting}>
        Update password
      </Button>
    </form>
  );
}

function MissingToken() {
  return (
    <Alert variant="destructive">
      <AlertCircle /> This link is incomplete. Open the link from your email again, or request a new one.
    </Alert>
  );
}

/** Verifies an emailed token once on load (verify-email and guardian-consent pages). */
export function TokenAction({ kind }: { kind: "verify" | "consent" }) {
  const token = useSearchParams().get("token") ?? "";
  const [state, setState] = useState<{ status: "working" | "ok" | "error"; message: string }>({
    status: "working",
    message: "",
  });
  const ran = useRef(false); // tokens are single-use: never submit twice (e.g. StrictMode)

  useEffect(() => {
    if (!token || ran.current) return;
    ran.current = true;
    (kind === "verify" ? verifyEmail(token) : grantGuardianConsent(token))
      .then((r) => setState({ status: "ok", message: r.message }))
      .catch((e) =>
        setState({ status: "error", message: e instanceof ApiError ? e.message : "Something went wrong." }),
      );
  }, [token, kind]);

  if (!token) return <MissingToken />;
  if (state.status === "working") {
    return (
      <p className="text-muted-foreground flex items-center gap-2 text-sm">
        <Loader2 className="size-4 animate-spin" /> {kind === "verify" ? "Verifying your email…" : "Recording consent…"}
      </p>
    );
  }
  return (
    <div className="space-y-4">
      <Alert variant={state.status === "ok" ? "success" : "destructive"}>
        {state.status === "ok" ? <CheckCircle2 /> : <AlertCircle />} {state.message}
      </Alert>
      {kind === "verify" && (
        <Button asChild variant="gradient" className="w-full">
          <Link href="/login">Continue to sign in</Link>
        </Button>
      )}
    </div>
  );
}
