/**
 * Design doc §19.1 — the first milestone, end to end in a real browser:
 * register → onboarding (Class 11 CBSE Physics) → Laws of Motion → adaptive session →
 * server-evaluated answers → knowledge model updates → next question → session report →
 * weak concepts in the revision plan / error notebook → dashboard from real data.
 *
 * Needs the sample content: `python -m scripts.seed_sample_content` on the E2E database.
 */
import { type APIRequestContext, expect, type Page, test } from "@playwright/test";
import { API, createAdmin, emailedLink, PASSWORD, uniqueEmail } from "./helpers";

type Q = {
  question_id: string;
  type: string;
  content: { options?: { id: string; text: string }[]; left?: { id: string }[]; blanks?: number };
};
type Delivery = { finished: boolean; question: Q };

async function adminToken(request: APIRequestContext) {
  const email = await createAdmin(request);
  const r = await request.post(`${API}/api/v1/auth/admin/login`, { data: { email, password: PASSWORD } });
  return { email, token: (await r.json()).access_token as string };
}

/** Reads the answer key through the admin API — the student payload never contains it. */
async function answerKey(request: APIRequestContext, token: string, questionId: string) {
  const r = await request.get(`${API}/api/v1/admin/questions/${questionId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return (await r.json()).latest.answer as Record<string, unknown>;
}

async function answer(page: Page, q: Q, key: Record<string, unknown>, correct: boolean) {
  const opts = q.content.options ?? [];
  const optionLabel = (id: string) =>
    page
      .locator("label")
      .filter({ hasText: opts.find((o) => o.id === id)!.text })
      .first();
  switch (q.type) {
    case "mcq_single":
    case "assertion_reason":
    case "diagram": {
      const right = key.correct as string;
      await optionLabel(correct ? right : opts.find((o) => o.id !== right)!.id).click();
      break;
    }
    case "mcq_multi": {
      const right = key.correct as string[];
      for (const id of correct ? right : [opts.find((o) => !right.includes(o.id))!.id]) await optionLabel(id).click();
      break;
    }
    case "numerical":
    case "integer":
      await page.getByLabel("Your answer").fill(String(correct ? key.value : Number(key.value) + 97));
      break;
    case "fill_blank": {
      const acc = key.accepted as string[][];
      for (let i = 0; i < acc.length; i++) await page.getByLabel(`Blank ${i + 1}`).fill(correct ? acc[i][0] : "zzz");
      break;
    }
    case "match": {
      const pairs = key.pairs as Record<string, string>;
      const selects = page.getByRole("combobox", { name: /^Match for/ });
      const ids = Object.keys(pairs);
      for (let i = 0; i < ids.length; i++) {
        const target = correct ? pairs[ids[i]] : pairs[ids[(i + 1) % ids.length]];
        await selects.nth(i).selectOption(target);
      }
      break;
    }
    case "subjective":
      await page.getByLabel("Your answer").fill("Explanation");
      break;
  }
  await page.getByRole("button", { name: "Submit answer" }).click();
}

test("first milestone: adaptive practice end to end", async ({ page, request }) => {
  test.setTimeout(120_000);
  const admin = await adminToken(request);

  // Register + verify, then sign in through the UI.
  const email = uniqueEmail("milestone");
  const reg = await request.post(`${API}/api/v1/auth/register`, {
    data: { email, password: PASSWORD, display_name: "Meera Iyer", is_minor: false, accept_terms: true },
  });
  expect(reg.status()).toBe(201);
  if ((await reg.json()).status === "pending_verification") {
    await page.goto(await emailedLink(request, email, "/verify-email"));
    await expect(page.getByText(/Email verified/)).toBeVisible();
  }
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();

  // 1. Onboarding is required before anything else.
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByRole("button", { name: /CBSE Class 11/ }).click();
  await expect(page.getByRole("button", { name: "Physics" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: /Score well in my board exams/ }).click();
  await page.getByRole("button", { name: "Start learning" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Recommended next")).toBeVisible();

  // 2. Curriculum → Laws of Motion → its concepts.
  await page.getByRole("link", { name: "My Curriculum" }).click();
  const chapter = page.getByRole("button", { name: /Laws of Motion/ });
  if ((await chapter.getAttribute("aria-expanded")) !== "true") await chapter.click();
  await expect(page.getByRole("link", { name: "Newton's second law (F = ma)" })).toBeVisible();

  // 3. Adaptive session for the chapter.
  const firstQ = page.waitForResponse((r) => r.url().includes("/next") && r.request().method() === "POST");
  await page
    .locator("div")
    .filter({ has: page.getByText("Laws of Motion", { exact: true }) })
    .getByRole("button", { name: "Practise" })
    .first()
    .click();
  await expect(page).toHaveURL(/\/practice\/[0-9a-f-]{36}$/);
  const d1 = (await (await firstQ).json()) as Delivery;
  expect(JSON.stringify(d1)).not.toMatch(/"(answer|solution|accepted|model_answer)"/); // no answer data

  // 4. A correct answer: server evaluates, mastery goes up, the reason is explained.
  await expect(page.getByText("Why this question:")).toBeVisible();
  await answer(page, d1.question, await answerKey(request, admin.token, d1.question.question_id), true);
  await expect(page.getByText("Correct", { exact: true })).toBeVisible();
  await expect(page.getByText("Solution", { exact: true })).toBeVisible();
  await expect(page.locator("li").filter({ hasText: "→" }).first()).toBeVisible();

  // 5. Next question, answered wrongly.
  const secondQ = page.waitForResponse((r) => r.url().includes("/next") && r.request().method() === "POST");
  await page.getByRole("button", { name: /Next question/ }).click();
  const d2 = (await (await secondQ).json()) as Delivery;
  expect(d2.question.question_id).not.toBe(d1.question.question_id); // never repeats in a session
  await answer(page, d2.question, await answerKey(request, admin.token, d2.question.question_id), false);
  await expect(page.getByText(/Not quite|Partly correct|Answer saved/)).toBeVisible();

  // 6. Finish → session report.
  await page.getByRole("button", { name: "Finish now" }).click();
  await expect(page).toHaveURL(/\/report$/);
  await expect(page.getByRole("heading", { name: "Session report" })).toBeVisible();
  await expect(page.getByText("1 of 2 correct")).toBeVisible();
  await expect(page.getByText("Mastery changes")).toBeVisible();

  // 7. The mistake is in the error notebook with its solution.
  await page.getByRole("link", { name: "Error Notebook" }).click();
  await expect(page.getByText(/Wrong 1×/).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Reattempt" }).first()).toBeVisible();

  // 8. Revision was scheduled from the evidence.
  await page.getByRole("link", { name: "Revision", exact: true }).click();
  await expect(page.getByText("Coming up")).toBeVisible();

  // 9. Dashboard figures come from the two real answers.
  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(
    page
      .locator("div")
      .filter({ hasText: /^Questions attempted2$/ })
      .first(),
  ).toBeVisible();
  await expect(
    page
      .locator("div")
      .filter({ hasText: /^Accuracy50%$/ })
      .first(),
  ).toBeVisible();
});

test("admin creates, previews and publishes a question", async ({ page, request }) => {
  const admin = await adminToken(request);
  await page.goto("/admin/login");
  await page.getByLabel("Email").fill(admin.email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin$/);

  await page.getByRole("link", { name: "Question Bank" }).click();
  await expect(page.getByText("Approval backlog", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "New question" }).click();

  const stem = `E2E: what is the unit of force? ${Date.now()}`;
  await page.getByLabel("Question text").fill(stem);
  await page.getByLabel("Option A", { exact: true }).fill("Newton");
  await page.getByLabel("Option B", { exact: true }).fill("Joule");
  await page.getByLabel("Option C", { exact: true }).fill("Watt");
  await page.getByLabel("Option D", { exact: true }).fill("Pascal");
  await page.getByLabel("Worked solution").fill("Force is measured in newtons (N).");
  await page.getByLabel("Newton's second law (F = ma)").check();
  await expect(page.getByText("Student preview")).toBeVisible();

  await page.getByRole("button", { name: "Create draft" }).click();
  await expect(page).toHaveURL(/\/admin\/questions\/[0-9a-f-]{36}$/);
  await expect(page.getByText("Draft", { exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: "Approve & publish" }).click();
  await expect(page.getByText(/Published — students can now get this question/)).toBeVisible();

  await page.getByRole("link", { name: "Question bank", exact: true }).click();
  await page.getByLabel("Search questions").fill(stem.slice(-13));
  await expect(page.getByRole("row").filter({ hasText: "Published" })).toHaveCount(1);
});
