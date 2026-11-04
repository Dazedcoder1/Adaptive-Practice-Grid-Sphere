import { expect, test } from "@playwright/test";
import { createAdmin, emailedLink, PASSWORD, uniqueEmail } from "./helpers";

test("super admin sees real stats, suspends and reactivates a student", async ({ page, browser, request }) => {
  const adminEmail = await createAdmin(request);

  // A verified student with an active session in another browser.
  const studentEmail = uniqueEmail("ravi");
  const reg = await request.post("http://localhost:8000/api/v1/auth/register", {
    data: { email: studentEmail, password: PASSWORD, display_name: "Ravi", is_minor: false, accept_terms: true },
  });
  expect(reg.status()).toBe(201);
  const studentCtx = await browser.newContext();
  const student = await studentCtx.newPage();
  await student.goto(await emailedLink(request, studentEmail, "/verify-email"));
  await expect(student.getByText(/Email verified/)).toBeVisible();
  await student.goto("/login");
  await student.getByLabel("Email").fill(studentEmail);
  await student.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await student.getByRole("button", { name: "Sign in" }).click();
  await expect(student).toHaveURL(/\/(dashboard|onboarding)$/);

  // Students can't use the admin portal.
  await student.goto("/admin");
  await expect(student).toHaveURL(/\/(dashboard|onboarding)$/);

  await page.goto("/admin/login");
  await page.getByLabel("Email").fill(adminEmail);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByText("Registered students")).toBeVisible();
  await expect(page.getByText(/Available once those modules ship/)).toBeVisible();

  await page.getByRole("link", { name: "User Management" }).click();
  await page.getByLabel("Search users").fill(studentEmail);
  await page.getByText(studentEmail).click();
  await expect(page.getByRole("heading", { name: "Ravi" })).toBeVisible();

  await page.getByRole("button", { name: "Suspend" }).click();
  await page.getByLabel("Reason").fill("E2E check");
  await page.getByRole("button", { name: "Suspend account" }).click();
  await expect(page.getByText("Account suspended and signed out everywhere")).toBeVisible();

  // The student's session dies immediately: next API call fails, they land on login.
  await student.goto("/profile");
  await expect(student).toHaveURL(/\/login/);

  await page.getByRole("button", { name: "Activate" }).click();
  await page.getByRole("button", { name: "Activate account" }).click();
  await expect(page.getByText("Account activated")).toBeVisible();

  await page.getByRole("link", { name: "Audit Logs" }).click();
  await page.getByLabel("Filter by action").fill("user.suspended");
  await expect(page.getByText(adminEmail).first()).toBeVisible();

  await studentCtx.close();
});
