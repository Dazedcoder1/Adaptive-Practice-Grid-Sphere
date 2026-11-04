"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, MailCheck } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { ApiError } from "@/services/api";
import { login, type Portal, resendGuardianConsent, resendVerification } from "../api";
import { safeNext } from "../guards";
import { type LoginValues, loginSchema } from "../schemas";

export function LoginForm({ portal }: { portal: Portal }) {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<ApiError | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [resending, setResending] = useState(false);
  const form = useForm<LoginValues>({ resolver: zodResolver(loginSchema), defaultValues: { email: "", password: "" } });
  const { errors, isSubmitting } = form.formState;

  async function onSubmit(v: LoginValues) {
    setError(null);
    setNotice(null);
    try {
      await login(portal, v.email, v.password);
      router.replace(safeNext(params.get("next"), portal === "admin" ? "/admin" : "/dashboard"));
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, "unknown", "Something went wrong."));
    }
  }

  async function resend() {
    setResending(true);
    const email = form.getValues("email");
    const r = await (
      error?.code === "guardian_consent_pending" ? resendGuardianConsent(email) : resendVerification(email)
    ).catch((e: ApiError) => ({ message: e.message }));
    setNotice(r.message);
    setResending(false);
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {params.get("reset") === "1" && !error && (
        <Alert variant="success">
          <MailCheck /> Password updated — sign in with your new password.
        </Alert>
      )}
      {error && (
        <Alert variant="destructive">
          <AlertCircle />
          <div className="space-y-2">
            <p>{error.message}</p>
            {(error.code === "email_not_verified" || error.code === "guardian_consent_pending") && (
              <Button type="button" variant="outline" size="sm" loading={resending} onClick={resend}>
                {error.code === "email_not_verified"
                  ? "Resend verification email"
                  : "Resend consent request to guardian"}
              </Button>
            )}
            {error.code === "use_admin_portal" && (
              <Link className="text-primary font-medium underline" href="/admin/login">
                Go to the admin sign-in
              </Link>
            )}
          </div>
        </Alert>
      )}
      {notice && (
        <Alert variant="info">
          <MailCheck /> {notice}
        </Alert>
      )}
      <FormField id="email" label="Email" error={errors.email?.message}>
        <Input type="email" autoComplete="email" autoFocus {...form.register("email")} />
      </FormField>
      <FormField id="password" label="Password" error={errors.password?.message}>
        <PasswordInput autoComplete="current-password" {...form.register("password")} />
      </FormField>
      <div className="flex justify-end">
        <Link href="/forgot-password" className="text-primary text-sm hover:underline">
          Forgot password?
        </Link>
      </div>
      <Button type="submit" variant="gradient" className="w-full" size="lg" loading={isSubmitting}>
        Sign in
      </Button>
    </form>
  );
}
