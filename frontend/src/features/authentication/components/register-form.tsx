"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, MailCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/ui/password-input";
import { cn } from "@/lib/utils";
import { ApiError } from "@/services/api";
import { register as registerApi } from "../api";
import { type RegisterValues, registerSchema } from "../schemas";

export function RegisterForm() {
  const [done, setDone] = useState<{ email: string; minor: boolean } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      display_name: "",
      email: "",
      password: "",
      confirm_password: "",
      is_minor: false,
      guardian_email: "",
      accept_terms: false,
    },
  });
  const { errors, isSubmitting } = form.formState;
  const isMinor = useWatch({ control: form.control, name: "is_minor" });

  async function onSubmit(v: RegisterValues) {
    setError(null);
    try {
      await registerApi(v);
      setDone({ email: v.email, minor: v.is_minor });
    } catch (e) {
      if (e instanceof ApiError) {
        for (const [field, msg] of Object.entries(e.fields)) {
          form.setError(field as keyof RegisterValues, { message: msg });
        }
        if (e.code === "email_taken") form.setError("email", { message: e.message });
        else setError(e.message);
      } else setError("Something went wrong. Please try again.");
    }
  }

  if (done) {
    return (
      <Alert variant="success" className="p-5">
        <MailCheck />
        <div className="space-y-2">
          <p className="font-medium">Check your inbox</p>
          <p className="text-muted-foreground">
            We sent a verification link to <strong className="text-foreground">{done.email}</strong>.
            {done.minor &&
              " After you verify, we'll email your parent or guardian to ask for their consent — you can sign in once they approve."}
          </p>
          <Link href="/login" className="text-primary inline-block font-medium hover:underline">
            Go to sign in
          </Link>
        </div>
      </Alert>
    );
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
      {error && (
        <Alert variant="destructive">
          <AlertCircle /> {error}
        </Alert>
      )}
      <FormField
        id="display_name"
        label="Your name"
        error={errors.display_name?.message}
        hint="Shown on your dashboard."
      >
        <Input autoComplete="nickname" autoFocus {...form.register("display_name")} />
      </FormField>
      <FormField id="email" label="Email" error={errors.email?.message}>
        <Input type="email" autoComplete="email" {...form.register("email")} />
      </FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField
          id="password"
          label="Password"
          error={errors.password?.message}
          hint="10+ characters, letters and numbers."
        >
          <PasswordInput autoComplete="new-password" {...form.register("password")} />
        </FormField>
        <FormField id="confirm_password" label="Confirm password" error={errors.confirm_password?.message}>
          <PasswordInput autoComplete="new-password" {...form.register("confirm_password")} />
        </FormField>
      </div>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Are you under 18?</legend>
        <Controller
          control={form.control}
          name="is_minor"
          render={({ field }) => (
            <div className="grid grid-cols-2 gap-2" role="radiogroup">
              {[
                { v: false, label: "18 or over" },
                { v: true, label: "Under 18" },
              ].map((o) => (
                <button
                  key={String(o.v)}
                  type="button"
                  role="radio"
                  aria-checked={field.value === o.v}
                  onClick={() => field.onChange(o.v)}
                  className={cn(
                    "h-10 rounded-lg border text-sm transition-colors",
                    field.value === o.v
                      ? "border-primary bg-primary/5 text-primary font-medium"
                      : "bg-card hover:bg-muted",
                  )}
                >
                  {o.label}
                </button>
              ))}
            </div>
          )}
        />
        <p className="text-muted-foreground text-xs">
          We only ask this to know whether a parent or guardian needs to consent. We don&apos;t store your date of
          birth.
        </p>
      </fieldset>

      {isMinor && (
        <FormField id="guardian_email" label="Parent or guardian's email" error={errors.guardian_email?.message}>
          <Input type="email" autoComplete="off" {...form.register("guardian_email")} />
        </FormField>
      )}

      <div className="space-y-1">
        <div className="flex items-start gap-2.5">
          <Controller
            control={form.control}
            name="accept_terms"
            render={({ field }) => (
              <Checkbox
                id="accept_terms"
                checked={field.value}
                onCheckedChange={(c) => field.onChange(c === true)}
                aria-invalid={!!errors.accept_terms}
                className="mt-0.5"
              />
            )}
          />
          <Label htmlFor="accept_terms" className="text-muted-foreground text-sm leading-snug font-normal">
            I agree to the Terms of Service and Privacy Policy, including how my learning data is used to personalise my
            practice.
          </Label>
        </div>
        {errors.accept_terms && <p className="text-destructive text-xs">{errors.accept_terms.message}</p>}
      </div>

      <Button type="submit" variant="gradient" className="w-full" size="lg" loading={isSubmitting}>
        Create account
      </Button>
    </form>
  );
}
