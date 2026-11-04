import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RegisterForm } from "./register-form";

describe("RegisterForm controls", () => {
  it("ticks the terms checkbox by clicking the box or its label", async () => {
    render(<RegisterForm />);
    const box = screen.getByRole("checkbox");
    expect(box).toHaveAttribute("aria-checked", "false");
    await userEvent.click(box);
    expect(box).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByText(/I agree to the Terms/));
    expect(box).toHaveAttribute("aria-checked", "false");
  });

  it("shows and hides the password with the eye button", async () => {
    render(<RegisterForm />);
    const input = screen.getByLabelText("Password", { selector: "input" });
    const [eye] = screen.getAllByRole("button", { name: "Show password" });
    expect(input).toHaveAttribute("type", "password");
    await userEvent.click(eye);
    expect(input).toHaveAttribute("type", "text");
    await userEvent.click(screen.getAllByRole("button", { name: "Hide password" })[0]);
    expect(input).toHaveAttribute("type", "password");
  });

  it("shows validation messages for invalid input", async () => {
    render(<RegisterForm />);
    await userEvent.type(screen.getByLabelText("Email"), "test@mail");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
    expect(screen.getByText("You need to accept the terms to continue.")).toBeInTheDocument();
  });
});

describe("RegisterForm success screen", () => {
  async function submitValid(status: string) {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ user_id: "u1", status, message: "" }), { status: 201 }),
    );
    render(<RegisterForm />);
    await userEvent.type(screen.getByLabelText("Your name"), "Asha");
    await userEvent.type(screen.getByLabelText("Email"), "asha@example.com");
    await userEvent.type(screen.getByLabelText("Password", { selector: "input" }), "Str0ngPassw0rd");
    await userEvent.type(screen.getByLabelText("Confirm password", { selector: "input" }), "Str0ngPassw0rd");
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
  }

  it("goes straight to sign-in when no verification is needed", async () => {
    await submitValid("active");
    expect(await screen.findByText("Account created")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
    expect(screen.queryByText(/verification link/)).not.toBeInTheDocument();
  });

  it("explains guardian consent for under-18s", async () => {
    await submitValid("pending_consent");
    expect(await screen.findByText(/emailed your parent or guardian/)).toBeInTheDocument();
  });
});
