import { z } from "zod";

/** Mirrors backend rules (identity/schemas.py) so users see errors before submitting. */
export const passwordSchema = z
  .string()
  .min(10, "Use at least 10 characters.")
  .max(128, "Use at most 128 characters.")
  .refine((v) => /[a-zA-Z]/.test(v) && /\d/.test(v), "Include at least one letter and one number.");

const email = z.email("Enter a valid email address.").max(320);

export const loginSchema = z.object({
  email,
  password: z.string().min(1, "Enter your password."),
});
export type LoginValues = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    display_name: z.string().trim().min(1, "Tell us what to call you.").max(80),
    email,
    password: passwordSchema,
    confirm_password: z.string(),
    is_minor: z.boolean(),
    guardian_email: z.string().optional(),
    accept_terms: z.boolean().refine((v) => v, "You need to accept the terms to continue."),
  })
  .superRefine((v, ctx) => {
    if (v.password !== v.confirm_password) {
      ctx.addIssue({ code: "custom", path: ["confirm_password"], message: "Passwords don't match." });
    }
    if (v.password && v.password.toLowerCase() === v.email.toLowerCase()) {
      ctx.addIssue({ code: "custom", path: ["password"], message: "Password can't be your email." });
    }
    if (v.is_minor) {
      const g = email.safeParse(v.guardian_email ?? "");
      if (!g.success) {
        ctx.addIssue({ code: "custom", path: ["guardian_email"], message: "Enter your parent or guardian's email." });
      } else if (g.data.toLowerCase() === v.email.toLowerCase()) {
        ctx.addIssue({ code: "custom", path: ["guardian_email"], message: "This must be different from your email." });
      }
    }
  });
export type RegisterValues = z.infer<typeof registerSchema>;

export const emailOnlySchema = z.object({ email });
export type EmailOnlyValues = z.infer<typeof emailOnlySchema>;

export const resetPasswordSchema = z
  .object({ new_password: passwordSchema, confirm_password: z.string() })
  .refine((v) => v.new_password === v.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords don't match.",
  });
export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Enter your current password."),
    new_password: passwordSchema,
    confirm_password: z.string(),
  })
  .refine((v) => v.new_password === v.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords don't match.",
  });
export type ChangePasswordValues = z.infer<typeof changePasswordSchema>;
