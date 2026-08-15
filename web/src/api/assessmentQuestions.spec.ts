import { describe, expect, it, vi } from "vitest";
import type { ScaleAnswer } from "../stores/assessmentAnswers";
import { generateAssessmentQuestions } from "./assessmentQuestions";
import { api } from "./client";
import { waitForJob } from "./jobs";

vi.mock("./client", () => ({
  api: { post: vi.fn() },
}));
vi.mock("./jobs", () => ({
  waitForJob: vi.fn(),
}));

const scaleAnswers: ScaleAnswer[] = [
  { area: "CAREER", question_kind: "SATISFACTION", item_code: "CAREER_FULFILLMENT", score: 4 },
];

describe("generateAssessmentQuestions", () => {
  it("POST /ai/assessment-questions を呼び、ジョブ完了を待って結果を返す", async () => {
    vi.mocked(api.post).mockResolvedValue({ job_id: "job-1", poll_after_ms: 1500 });
    vi.mocked(waitForJob).mockResolvedValue({
      questions: [{ area: "CAREER", slot: "SATISFIED", target_item_code: "CAREER_FULFILLMENT", text: "..." }],
    });

    const result = await generateAssessmentQuestions(scaleAnswers, "2026-08-v1");

    expect(api.post).toHaveBeenCalledWith(
      "/ai/assessment-questions",
      { scale_answers: scaleAnswers, question_set_version: "2026-08-v1" },
      { signal: undefined },
    );
    expect(waitForJob).toHaveBeenCalledWith("job-1", 1500, undefined);
    expect(result).toEqual([
      { area: "CAREER", slot: "SATISFIED", target_item_code: "CAREER_FULFILLMENT", text: "..." },
    ]);
  });

  it("AbortSignalをジョブ作成・ポーリングの両方に渡す", async () => {
    vi.mocked(api.post).mockResolvedValue({ job_id: "job-1", poll_after_ms: 1500 });
    vi.mocked(waitForJob).mockResolvedValue({ questions: [] });
    const controller = new AbortController();

    await generateAssessmentQuestions(scaleAnswers, "2026-08-v1", controller.signal);

    expect(api.post).toHaveBeenCalledWith(expect.any(String), expect.any(Object), {
      signal: controller.signal,
    });
    expect(waitForJob).toHaveBeenCalledWith("job-1", 1500, controller.signal);
  });
});
