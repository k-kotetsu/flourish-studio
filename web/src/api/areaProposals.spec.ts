import { describe, expect, it, vi } from "vitest";
import type { AreaDialogueChoice, AreaDialogueMessage } from "./areaDialogue";
import { generateAreaProposals } from "./areaProposals";
import { api } from "./client";
import { waitForJob } from "./jobs";

vi.mock("./client", () => ({
  api: { post: vi.fn() },
}));
vi.mock("./jobs", () => ({
  waitForJob: vi.fn(),
}));

const choices: AreaDialogueChoice[] = [
  { question_code: "Q1", option_codes: ["CAREER_OUTLOOK"] },
  { question_code: "Q2", option_codes: ["CAREER_VALUE_GROWTH"] },
  { question_code: "Q3", option_codes: ["CAREER_POSITION_GROWTH"] },
];
const messages: AreaDialogueMessage[] = [
  { role: "AI", body: "問い" },
  { role: "USER", body: "回答" },
];

describe("generateAreaProposals", () => {
  it("POST /ai/area-proposals を呼び、ジョブ完了を待って結果を返す", async () => {
    vi.mocked(api.post).mockResolvedValue({ job_id: "job-1", poll_after_ms: 1500 });
    vi.mocked(waitForJob).mockResolvedValue({
      proposals: [
        { direction: "DEEPEN", label: "今の場所で深める", ideal_state: "…できている。" },
        { direction: "CHANGE", label: "やり方を変える", ideal_state: "…見つかっている。" },
        { direction: "EXPAND", label: "外に出る", ideal_state: "…持てている。" },
      ],
      safety_flag: false,
    });

    const result = await generateAreaProposals("CAREER", choices, messages);

    expect(api.post).toHaveBeenCalledWith(
      "/ai/area-proposals",
      { area: "CAREER", choices, messages },
      { signal: undefined },
    );
    expect(waitForJob).toHaveBeenCalledWith("job-1", 1500, undefined);
    expect(result.proposals).toHaveLength(3);
  });

  it("AbortSignalをジョブ作成・ポーリングの両方に渡す", async () => {
    vi.mocked(api.post).mockResolvedValue({ job_id: "job-1", poll_after_ms: 1500 });
    vi.mocked(waitForJob).mockResolvedValue({ proposals: [], safety_flag: false });
    const controller = new AbortController();

    await generateAreaProposals("CAREER", choices, messages, controller.signal);

    expect(api.post).toHaveBeenCalledWith(expect.any(String), expect.any(Object), {
      signal: controller.signal,
    });
    expect(waitForJob).toHaveBeenCalledWith("job-1", 1500, controller.signal);
  });
});
