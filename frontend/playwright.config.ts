import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests against a running stack:
 *   backend with ENVIRONMENT=test (exposes the test-only email inbox) on :8000
 *   frontend (`npm run build && npm start`, or `npm run dev`) on :3000
 * See README → "End-to-end tests".
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      // PW_CHANNEL=chrome uses an installed Google Chrome instead of Playwright's Chromium.
      use: { ...devices["Desktop Chrome"], channel: process.env.PW_CHANNEL || undefined },
      grepInvert: /@mobile/,
    },
    { name: "mobile", use: { ...devices["Pixel 7"], channel: process.env.PW_CHANNEL || undefined }, grep: /@mobile/ },
  ],
});
