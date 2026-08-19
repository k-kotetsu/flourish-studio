import { describe, expect, it, vi } from "vitest";
import { login, register } from "./auth";
import { api } from "./client";

vi.mock("./client", () => ({
  api: { post: vi.fn() },
}));

describe("login", () => {
  it("POST /auth/login をemail・passwordで呼ぶ", async () => {
    vi.mocked(api.post).mockResolvedValue(undefined);

    await login("user@example.com", "correct-horse-battery-9");

    expect(api.post).toHaveBeenCalledWith("/auth/login", {
      email: "user@example.com",
      password: "correct-horse-battery-9",
    });
  });
});

describe("register", () => {
  it("POST /auth/register をemail・passwordで呼ぶ", async () => {
    vi.mocked(api.post).mockResolvedValue(undefined);

    await register("user@example.com", "correct-horse-battery-9");

    expect(api.post).toHaveBeenCalledWith("/auth/register", {
      email: "user@example.com",
      password: "correct-horse-battery-9",
    });
  });
});
