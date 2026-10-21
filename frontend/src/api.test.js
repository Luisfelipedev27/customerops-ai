import { afterEach, expect, it, vi } from "vitest";
import { api } from "./api";

afterEach(() => vi.unstubAllGlobals());

it("reports non-JSON server errors without exposing a parser error", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      status: 502,
      ok: false,
      json: async () => {
        throw new SyntaxError("Unexpected token <");
      },
    }),
  );
  await expect(api("/customers")).rejects.toThrow("Request failed (502)");
});

it("accepts an empty successful response", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ status: 204 }));
  await expect(api("/auth/logout")).resolves.toBeNull();
});
