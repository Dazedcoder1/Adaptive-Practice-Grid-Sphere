import { describe, expect, it } from "vitest";
import { safeNext } from "./guards";

describe("safeNext (open-redirect protection)", () => {
  it.each([
    ["/profile", "/profile"],
    ["//evil.com", "/dashboard"],
    ["https://evil.com", "/dashboard"],
    [null, "/dashboard"],
  ])("%s → %s", (input, out) => {
    expect(safeNext(input, "/dashboard")).toBe(out);
  });
});
