import { describe, expect, it } from "vitest";
import { passwordSchema, registerSchema } from "./schemas";

const base = {
  display_name: "Asha",
  email: "asha@example.com",
  password: "Str0ngPassw0rd",
  confirm_password: "Str0ngPassw0rd",
  is_minor: false,
  guardian_email: "",
  accept_terms: true,
};

const fieldErrors = (v: unknown) => {
  const r = registerSchema.safeParse(v);
  return r.success ? {} : Object.fromEntries(r.error.issues.map((i) => [i.path.join("."), i.message]));
};

describe("password rules (mirror the backend)", () => {
  it.each([
    ["short1", false],
    ["onlyletterslong", false],
    ["1234567890", false],
    ["Str0ngPassw0rd", true],
  ])("%s → valid=%s", (pw, ok) => {
    expect(passwordSchema.safeParse(pw).success).toBe(ok);
  });
});

describe("registerSchema", () => {
  it("accepts a valid adult registration", () => {
    expect(fieldErrors(base)).toEqual({});
  });

  it("requires matching passwords and accepted terms", () => {
    const e = fieldErrors({ ...base, confirm_password: "Different1234", accept_terms: false });
    expect(e.confirm_password).toMatch(/match/);
    expect(e.accept_terms).toBeDefined();
  });

  it("requires a guardian email for minors, distinct from the student's", () => {
    expect(fieldErrors({ ...base, is_minor: true }).guardian_email).toBeDefined();
    expect(fieldErrors({ ...base, is_minor: true, guardian_email: "ASHA@example.com" }).guardian_email).toMatch(
      /different/,
    );
    expect(fieldErrors({ ...base, is_minor: true, guardian_email: "parent@example.com" })).toEqual({});
  });

  it("rejects using the email as the password", () => {
    const e = fieldErrors({
      ...base,
      email: "asha12345@ex.co",
      password: "asha12345@ex.co",
      confirm_password: "asha12345@ex.co",
    });
    expect(e.password).toMatch(/email/);
  });
});
