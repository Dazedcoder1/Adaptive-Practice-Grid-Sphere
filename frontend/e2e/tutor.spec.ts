/**
 * Phase 2a in a real browser: the AI tutor (notes mode — no provider configured in E2E) and
 * the admin document pipeline. Needs the sample content (`python -m scripts.seed_sample_content`).
 */
import { type APIRequestContext, expect, type Page, test } from "@playwright/test";
import { API, createAdmin, emailedLink, PASSWORD, uniqueEmail } from "./helpers";

async function onboardedStudent(page: Page, request: APIRequestContext) {
  const email = uniqueEmail("tutor");
  const reg = await request.post(`${API}/api/v1/auth/register`, {
    data: { email, password: PASSWORD, display_name: "Kabir Rao", is_minor: false, accept_terms: true },
  });
  expect(reg.status()).toBe(201);
  if ((await reg.json()).status === "pending_verification") {
    const link = await emailedLink(request, email, "/verify-email");
    const token = new URL(link, "http://x").searchParams.get("token");
    await request.post(`${API}/api/v1/auth/verify-email`, { data: { token } });
  }
  const login = await request.post(`${API}/api/v1/auth/login`, { data: { email, password: PASSWORD } });
  const h = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const opts = await (await request.get(`${API}/api/v1/curriculum/options`, { headers: h })).json();
  const cur = opts.boards.find((b: { code: string }) => b.code === "CBSE").curricula[0];
  const r = await request.put(`${API}/api/v1/students/me/onboarding`, {
    headers: h,
    data: {
      study_mode: "school",
      curriculum_id: cur.id,
      subject_ids: cur.subjects.map((s: { id: number }) => s.id),
      goals: ["strengthen_basics"],
      weekly_days: 5,
      minutes_per_day: 30,
    },
  });
  expect(r.status()).toBe(200);
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

test("student asks the tutor from a concept page and in practice", async ({ page, request }) => {
  test.setTimeout(90_000);
  await onboardedStudent(page, request);

  // From the concept page → tutor, pre-set to that concept in Teach me mode.
  await page.getByRole("link", { name: "My Curriculum" }).click();
  const chapter = page.getByRole("button", { name: /Laws of Motion/ });
  if ((await chapter.getAttribute("aria-expanded")) !== "true") await chapter.click();
  await page.getByRole("link", { name: "Newton's third law" }).click();
  await page.getByRole("link", { name: "Ask the tutor" }).click();
  await expect(page).toHaveURL(/\/tutor\?concept=\d+&mode=teach$/);
  await expect(page.getByRole("radio", { name: /Teach me/ })).toHaveAttribute("aria-checked", "true");
  await expect(page.locator("#tutor-concept")).toHaveValue(/\d+/);
  await expect(page.getByRole("alert").filter({ hasText: "isn't switched on yet" })).toBeVisible();

  await page.getByLabel("Message the tutor").fill("What are action and reaction pairs?");
  await page.keyboard.press("Enter");
  await expect(page.getByText("From your study notes").first()).toBeVisible();
  await expect(page.getByText("Sources")).toBeVisible();
  await expect(page.locator("summary").filter({ hasText: "Newton's third law" }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: /^Teach me: Newton's third law/ })).toBeVisible(); // history

  // In practice: the tutor panel beside a question.
  await page.getByRole("link", { name: "Practice", exact: true }).click();
  await page.getByRole("link", { name: "My Curriculum" }).click();
  if ((await page.getByRole("button", { name: /Laws of Motion/ }).getAttribute("aria-expanded")) !== "true")
    await page.getByRole("button", { name: /Laws of Motion/ }).click();
  await page.getByRole("link", { name: "Connected bodies" }).click(); // every question here has hints
  await page.getByRole("button", { name: "Practise this concept" }).click();
  await expect(page).toHaveURL(/\/practice\/[0-9a-f-]{36}$/);
  await expect(page.getByText("Why this question:")).toBeVisible();
  await page.getByRole("button", { name: "Ask tutor" }).click();
  await expect(page.getByText("counts like a hint, so your mastery estimate stays honest")).toBeVisible();
  await page.getByRole("button", { name: "Give a hint" }).click();
  await expect(page.getByText(/Hint 1:/).first()).toBeVisible();
  // The hint opened by the tutor also appears on the question itself.
  await expect(page.getByRole("alert").filter({ hasText: "Hint 1:" })).toBeVisible();
});

test("admin uploads, reviews, approves and tests a document", async ({ page, request }) => {
  test.setTimeout(90_000);
  const email = await createAdmin(request);
  await page.goto("/admin/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin$/);

  await page.getByRole("link", { name: "AI & RAG" }).click();
  await expect(page.getByText("Approved documents")).toBeVisible();
  await expect(page.getByText("LLM_PROVIDER not set — notes mode")).toBeVisible();

  await page.getByRole("link", { name: "Documents", exact: true }).click();
  await expect(page.getByRole("row").filter({ hasText: "Laws of Motion — study notes" })).toBeVisible();

  const word = `zorbonium${Date.now()}`;
  await page.getByRole("button", { name: "Upload document" }).click();
  await page.getByLabel("File").setInputFiles({
    name: "zorbonium.md",
    mimeType: "text/markdown",
    buffer: Buffer.from(
      `# Extra notes\n\n## Friction and ${word}\n\nA ${word} block on a rough floor needs a push larger than the limiting static friction before it slides.\n`,
    ),
  });
  await page.getByLabel("Title").fill(`E2E notes ${word}`);
  await page.getByRole("button", { name: "Upload & process" }).click();
  await expect(page).toHaveURL(/\/admin\/ai\/documents\/[0-9a-f-]{36}$/);
  await expect(page.getByText("Needs review").first()).toBeVisible();
  await expect(page.getByText(`Friction and ${word}`)).toBeVisible();
  await page.getByRole("button", { name: "Approve for students" }).click();
  await expect(page.getByText("Approved", { exact: true }).first()).toBeVisible();

  await page.getByRole("link", { name: "Retrieval testing" }).click();
  await page.getByLabel("Query", { exact: true }).fill(`what is a ${word} block`);
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByText("keyword only")).toBeVisible();
  await expect(page.locator("li").filter({ hasText: `E2E notes ${word}` }).first()).toBeVisible();
});
