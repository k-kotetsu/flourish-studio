import { describe, expect, it, vi } from "vitest";
import { createGuestSession } from "./guestSessions";
import { api } from "./client";

vi.mock("./client", () => ({
  api: { post: vi.fn() },
}));

describe("createGuestSession", () => {
  it("POST /guest-sessions を呼ぶ", async () => {
    vi.mocked(api.post).mockResolvedValue(undefined);

    await createGuestSession();

    expect(api.post).toHaveBeenCalledWith("/guest-sessions");
  });
});
