import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, onUnauthorized } from "./client";

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

describe("api client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    onUnauthorized(null);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("GETは/api/v1配下をcredentials:includeで呼び、JSONを返す", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(200, { ok: true }));

    const result = await api.get<{ ok: boolean }>("/me");

    expect(result).toEqual({ ok: true });
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("/api/v1/me");
    expect(init?.credentials).toBe("include");
  });

  it("POSTはボディをJSONで送りContent-Typeを付ける", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(201, { id: "1" }));

    await api.post("/purposes", { statement: "育てる" });

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify({ statement: "育てる" }));
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("Idempotency-Keyを指定すればヘッダに付く", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(202, { job_id: "j1" }));

    await api.post("/assessments", { foo: "bar" }, { idempotencyKey: "key-1" });

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect((init?.headers as Record<string, string>)["Idempotency-Key"]).toBe("key-1");
  });

  it("204はundefinedを返す", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }));

    const result = await api.delete("/auth/logout");

    expect(result).toBeUndefined();
  });

  it("エラー応答はApiErrorとしてcode・message・detailsを保持する", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(422, {
        error: {
          code: "ANSWERS_INCOMPLETE",
          message: "scale answers must be exactly 24",
          details: [{ field: "scale_answers" }],
        },
      }),
    );

    await expect(api.get("/assessments/x")).rejects.toMatchObject({
      status: 422,
      code: "ANSWERS_INCOMPLETE",
      message: "scale answers must be exactly 24",
      details: [{ field: "scale_answers" }],
    });
  });

  it("429はRetry-AfterヘッダをretryAfterSecondsとして保持する", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(
        429,
        { error: { code: "RATE_LIMITED", message: "too many requests" } },
        { "Retry-After": "30" },
      ),
    );

    await expect(api.post("/assessments")).rejects.toMatchObject({
      status: 429,
      code: "RATE_LIMITED",
      retryAfterSeconds: 30,
    });
  });

  it("401はonUnauthorizedハンドラを呼ぶ", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(401, { error: { code: "UNAUTHENTICATED", message: "no session" } }),
    );
    const handler = vi.fn();
    onUnauthorized(handler);

    await expect(api.get("/me")).rejects.toBeInstanceOf(ApiError);
    expect(handler).toHaveBeenCalledOnce();
  });

  it("fetch自体が失敗したらNETWORK_ERRORとして投げる", async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError("network down"));

    await expect(api.get("/me")).rejects.toMatchObject({ code: "NETWORK_ERROR", status: 0 });
  });

  it("AbortErrorはApiErrorに包まずそのまま伝える", async () => {
    const abortError = new DOMException("aborted", "AbortError");
    vi.mocked(fetch).mockRejectedValue(abortError);

    await expect(api.get("/me")).rejects.toBe(abortError);
  });
});
