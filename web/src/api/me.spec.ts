import { describe, expect, it, vi } from "vitest";
import { api } from "./client";
import { updateThemePreference } from "./me";

vi.mock("./client", () => ({
  api: { patch: vi.fn() },
}));

describe("updateThemePreference", () => {
  it("PATCH /me にtheme_preferenceを送る", async () => {
    vi.mocked(api.patch).mockResolvedValue({ theme_preference: "DARK" });

    const result = await updateThemePreference("DARK");

    expect(api.patch).toHaveBeenCalledWith("/me", { theme_preference: "DARK" });
    expect(result).toEqual({ theme_preference: "DARK" });
  });
});
