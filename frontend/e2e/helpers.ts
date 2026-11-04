import { type APIRequestContext, expect } from "@playwright/test";

export const API = process.env.E2E_API_URL ?? "http://localhost:8000";
export const PASSWORD = "Str0ngPassw0rd";

export const uniqueEmail = (prefix: string) => `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;

/** Reads the newest emailed link for `path` from the backend's test-only inbox. */
export async function emailedLink(request: APIRequestContext, to: string, path: string) {
  let link: string | undefined;
  await expect
    .poll(async () => {
      const res = await request.get(`${API}/api/v1/__test__/emails?to=${encodeURIComponent(to)}`);
      const mails: { body: string }[] = await res.json();
      link = mails
        .map((m) => m.body.match(new RegExp(`https?://\\S+${path}\\?token=[\\w-]+`))?.[0])
        .filter(Boolean)
        .at(-1);
      return link;
    })
    .toBeTruthy();
  return new URL(link!).pathname + new URL(link!).search;
}

export async function createAdmin(request: APIRequestContext) {
  const email = uniqueEmail("admin");
  const res = await request.post(`${API}/api/v1/__test__/admins`, { data: { email, password: PASSWORD } });
  expect(res.status()).toBe(201);
  return email;
}
