import { describe, expect, it, vi } from "vitest";
import type { ScaleAnswer } from "../stores/assessmentAnswers";
import type { FreeTextAnswer } from "../stores/freeTextAnswers";
import { generateAssessmentReport } from "./assessments";
import { api } from "./client";
import { waitForJob } from "./jobs";

vi.mock("./client", () => ({
  api: { post: vi.fn(), get: vi.fn() },
}));
vi.mock("./jobs", () => ({
  waitForJob: vi.fn(),
}));

const scaleAnswers: ScaleAnswer[] = [
  { area: "CAREER", question_kind: "SATISFACTION", item_code: "CAREER_FULFILLMENT", score: 4 },
];
const freeTextAnswers: FreeTextAnswer[] = [
  {
    area: "CAREER",
    slot: "SATISFIED",
    target_item_code: "CAREER_FULFILLMENT",
    generated_question: "...",
    body: "",
  },
];
const result = {
  nickname: "全速前進、燃料計は未確認",
  articulation_stage: "SPROUT" as const,
  commitment_stage: "SEED" as const,
  commitment_score: 3,
  safety_flag: false,
  areas: [],
  generated_at: "2026-08-08T04:12:00Z",
};

describe("generateAssessmentReport", () => {
  it("POST /assessments → ジョブ完了待ち → GET /assessments/{id} の順に呼ぶ", async () => {
    vi.mocked(api.post).mockResolvedValue({ job_id: "job-1", poll_after_ms: 1500 });
    vi.mocked(waitForJob).mockResolvedValue({ assessment_id: "assessment-1" });
    vi.mocked(api.get).mockResolvedValue(result);

    const returned = await generateAssessmentReport(scaleAnswers, freeTextAnswers, "2026-08-v1");

    expect(api.post).toHaveBeenCalledWith(
      "/assessments",
      {
        scale_answers: scaleAnswers,
        free_text_answers: freeTextAnswers,
        question_set_version: "2026-08-v1",
      },
      { signal: undefined },
    );
    expect(waitForJob).toHaveBeenCalledWith("job-1", 1500, undefined);
    expect(api.get).toHaveBeenCalledWith("/assessments/assessment-1", { signal: undefined });
    expect(returned).toEqual(result);
  });

  it("AbortSignalをジョブ作成・ポーリング・結果取得のすべてに渡す", async () => {
    vi.mocked(api.post).mockResolvedValue({ job_id: "job-1", poll_after_ms: 1500 });
    vi.mocked(waitForJob).mockResolvedValue({ assessment_id: "assessment-1" });
    vi.mocked(api.get).mockResolvedValue(result);
    const controller = new AbortController();

    await generateAssessmentReport(
      scaleAnswers,
      freeTextAnswers,
      "2026-08-v1",
      controller.signal,
    );

    expect(api.post).toHaveBeenCalledWith(expect.any(String), expect.any(Object), {
      signal: controller.signal,
    });
    expect(waitForJob).toHaveBeenCalledWith("job-1", 1500, controller.signal);
    expect(api.get).toHaveBeenCalledWith(expect.any(String), { signal: controller.signal });
  });
});
