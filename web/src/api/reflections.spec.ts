import { describe, expect, it, vi } from "vitest";
import type { ReflectionStatusAnswer } from "../stores/reflectionAnswers";
import { generateReflection } from "./reflections";
import { api } from "./client";
import { waitForJob } from "./jobs";

vi.mock("./client", () => ({
  api: { post: vi.fn(), get: vi.fn() },
}));
vi.mock("./jobs", () => ({
  waitForJob: vi.fn(),
}));

const statuses: ReflectionStatusAnswer[] = [{ goal_key: "g-1", status: "ON_TRACK" }];
const result = {
  looking_back: "前に進みました。",
  insight: "小さく区切れると動けるようです。",
  next_step: "来週は1日1回だけ開いてみるのはどうでしょう。",
  safety_flag: false,
  generated_at: "2026-08-08T09:01:00Z",
  answered_at: "2026-08-08T09:00:00Z",
};

describe("generateReflection", () => {
  it("POST /reflections → ジョブ完了待ち → GET /reflections/{id} の順に呼ぶ", async () => {
    vi.mocked(api.post).mockResolvedValue({ job_id: "job-1", poll_after_ms: 1500 });
    vi.mocked(waitForJob).mockResolvedValue({ reflection_id: "reflection-1" });
    vi.mocked(api.get).mockResolvedValue(result);

    const returned = await generateReflection(statuses, "今週は時間が取れなかった");

    expect(api.post).toHaveBeenCalledWith(
      "/reflections",
      { statuses, note: "今週は時間が取れなかった" },
      { signal: undefined },
    );
    expect(waitForJob).toHaveBeenCalledWith("job-1", 1500, undefined);
    expect(api.get).toHaveBeenCalledWith("/reflections/reflection-1", { signal: undefined });
    expect(returned).toEqual(result);
  });

  it("AbortSignalをジョブ作成・ポーリング・結果取得のすべてに渡す", async () => {
    vi.mocked(api.post).mockResolvedValue({ job_id: "job-1", poll_after_ms: 1500 });
    vi.mocked(waitForJob).mockResolvedValue({ reflection_id: "reflection-1" });
    vi.mocked(api.get).mockResolvedValue(result);
    const controller = new AbortController();

    await generateReflection(statuses, null, controller.signal);

    expect(api.post).toHaveBeenCalledWith(expect.any(String), expect.any(Object), {
      signal: controller.signal,
    });
    expect(waitForJob).toHaveBeenCalledWith("job-1", 1500, controller.signal);
    expect(api.get).toHaveBeenCalledWith(expect.any(String), { signal: controller.signal });
  });
});
