import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/stores/auth";
import { router } from "@/test/setup";
import { LoginForm } from "./login-form";

function mockFetch(status: number, body: unknown) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(body), { status }));
}

async function fill(email: string, password: string) {
  await userEvent.type(screen.getByLabelText("Email"), email);
  await userEvent.type(screen.getByLabelText("Password"), password);
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("LoginForm", () => {
  beforeEach(() => {
    useAuthStore.getState().clear();
    router.replace.mockClear();
  });

  it("validates before calling the API", async () => {
    const fetch = mockFetch(200, {});
    render(<LoginForm portal="student" />);
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("signs in, stores the session in memory and redirects", async () => {
    const user = {
      id: "u1",
      email: "a@example.com",
      status: "active",
      roles: ["student"],
      permissions: [],
      display_name: "A",
      onboarding_completed: false,
    };
    const fetch = mockFetch(200, { access_token: "tok", token_type: "bearer", expires_in: 900, user });
    render(<LoginForm portal="student" />);
    await fill("a@example.com", "Str0ngPassw0rd");

    expect(fetch.mock.calls[0][0]).toMatch(/\/api\/v1\/auth\/login$/);
    expect((fetch.mock.calls[0][1] as RequestInit).credentials).toBe("include");
    expect(useAuthStore.getState().accessToken).toBe("tok");
    expect(router.replace).toHaveBeenCalledWith("/dashboard");
    expect(window.localStorage.length).toBe(0); // token never persisted
  });

  it("uses the admin endpoint for the admin portal", async () => {
    const fetch = mockFetch(401, { error: { code: "invalid_credentials", message: "Incorrect email or password." } });
    render(<LoginForm portal="admin" />);
    await fill("admin@example.com", "whatever123");
    expect(fetch.mock.calls[0][0]).toMatch(/\/auth\/admin\/login$/);
    expect(await screen.findByText("Incorrect email or password.")).toBeInTheDocument();
  });

  it("offers to resend verification when the email isn't verified", async () => {
    mockFetch(403, { error: { code: "email_not_verified", message: "Please verify your email first." } });
    render(<LoginForm portal="student" />);
    await fill("a@example.com", "Str0ngPassw0rd");
    expect(await screen.findByRole("button", { name: "Resend verification email" })).toBeInTheDocument();
  });
});
