import { expect, test } from "@playwright/test";
import { emailedLink, PASSWORD, uniqueEmail } from "./helpers";

test("student registers, verifies, signs in, edits profile and signs out", async ({ page, request }) => {
  const email = uniqueEmail("asha");

  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("own learning journey");
  await page.getByRole("link", { name: "Start learning free" }).click();

  await page.getByLabel("Your name").fill("Asha Rao");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password").fill(PASSWORD);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("Check your inbox")).toBeVisible();

  // Signing in before verifying is refused with a way to resend.
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("button", { name: "Resend verification email" })).toBeVisible();

  await page.goto(await emailedLink(request, email, "/verify-email"));
  await expect(page.getByText(/Email verified/)).toBeVisible();
  await page.getByRole("link", { name: "Continue to sign in" }).click();

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Asha");
  await expect(page.getByText("No activity yet").first()).toBeVisible(); // no fabricated metrics

  // Session survives a full reload (refresh cookie → new access token).
  await page.reload();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Asha");

  // Planned modules are clearly labelled.
  await page.getByRole("link", { name: /Practice/ }).click();
  await expect(page.getByText(/Planned · Phase 1/)).toBeVisible();

  await page.goto("/profile");
  await page.getByLabel("Name").fill("Asha R");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Profile saved")).toBeVisible();
  await expect(page.getByText("This device")).toBeVisible();

  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login\?next=%2Fdashboard/);
});

test("minor needs guardian consent before signing in", async ({ page, request }) => {
  const email = uniqueEmail("kid");
  const guardian = uniqueEmail("parent");
  await page.goto("/register");
  await page.getByLabel("Your name").fill("Kiran");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password").fill(PASSWORD);
  await page.getByRole("radio", { name: "Under 18" }).click();
  await page.getByLabel("Parent or guardian's email").fill(guardian);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText(/parent or guardian to ask for their consent/)).toBeVisible();

  await page.goto(await emailedLink(request, email, "/verify-email"));
  await expect(page.getByText(/asked your parent or guardian/)).toBeVisible();

  await page.goto(await emailedLink(request, guardian, "/guardian-consent"));
  await expect(page.getByText(/Consent recorded/)).toBeVisible();

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("landing page works on mobile @mobile", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Toggle menu" }).click();
  await page.getByRole("link", { name: "Get started" }).click();
  await expect(page).toHaveURL(/\/register$/);
});
