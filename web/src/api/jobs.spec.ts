import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { JobFailedError, waitForJob } from "./jobs";
import { api } from "./client";

vi.mock("./client", () => ({
  api: { get: vi.fn() },
}));

describe("waitForJob", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.mocked(api.get).mockReset();
  });

  it("初回はPOSTが返したpoll_after_msだけ待ってからGETする", async () => {
    vi.mocked(api.get).mockResolvedValue({ status: "SUCCEEDED", result: { id: "a1" } });

    const promise = waitForJob("job-1", 1500);
    await vi.advanceTimersByTimeAsync(1499);
    expect(api.get).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);

    await expect(promise).resolves.toEqual({ id: "a1" });
    expect(api.get).toHaveBeenCalledWith("/jobs/job-1", { signal: undefined });
  });

  it("QUEUED/RUNNINGが返す新しいpoll_after_msに従い、固定値を使わない", async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ status: "QUEUED", poll_after_ms: 1500 })
      .mockResolvedValueOnce({ status: "RUNNING", poll_after_ms: 4000 })
      .mockResolvedValueOnce({ status: "SUCCEEDED", result: { id: "a1" } });

    const promise = waitForJob("job-1", 1500);

    await vi.advanceTimersByTimeAsync(1500);
    expect(api.get).toHaveBeenCalledTimes(1);

    // サーバーが次にRUNNINGで指示した4000msに従う(1500msではまだ呼ばれない)
    await vi.advanceTimersByTimeAsync(1500);
    expect(api.get).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(2500);
    expect(api.get).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(1500);
    expect(api.get).toHaveBeenCalledTimes(3);

    await expect(promise).resolves.toEqual({ id: "a1" });
  });

  it("FAILEDならJobFailedErrorを投げ、code・retryableを保持する", async () => {
    vi.mocked(api.get).mockResolvedValue({
      status: "FAILED",
      error: { code: "AI_PROVIDER_ERROR", retryable: true },
    });

    const promise = waitForJob("job-1", 100);
    // タイマー進行中にrejectするため、アサーション到達前の未捕捉rejection警告を避ける
    promise.catch(() => {});
    await vi.advanceTimersByTimeAsync(100);

    await expect(promise).rejects.toBeInstanceOf(JobFailedError);
    await expect(promise).rejects.toMatchObject({ code: "AI_PROVIDER_ERROR", retryable: true });
  });

  it("QUEUED/RUNNING中にpoll_after_msが無ければ例外を投げる(P1-13の未実装箇所を検知する)", async () => {
    vi.mocked(api.get).mockResolvedValue({ status: "RUNNING" });

    const promise = waitForJob("job-1", 100);
    promise.catch(() => {});
    await vi.advanceTimersByTimeAsync(100);

    await expect(promise).rejects.toThrow(/poll_after_ms/);
  });
});
