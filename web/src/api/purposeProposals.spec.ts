import { describe, expect, it, vi } from "vitest";
import type { PurposeDialogueChoice, PurposeDialogueMessage } from "./purposeDialogue";
import { generatePurposeProposals } from "./purposeProposals";
import { api } from "./client";
import { waitForJob } from "./jobs";

vi.mock("./client", () => ({
  api: { post: vi.fn() },
}));
vi.mock("./jobs", () => ({
  waitForJob: vi.fn(),
}));

const choices: PurposeDialogueChoice[] = [
  { question_code: "Q1", option_codes: ["GROWTH"] },
  { question_code: "Q2", option_codes: ["SELF_DETERMINED"] },
  { question_code: "Q3", option_codes: ["HAVING_OPTIONS"] },
];
const messages: PurposeDialogueMessage[] = [
  { role: "AI", body: "問い" },
  { role: "USER", body: "回答" },
];

describe("generatePurposeProposals", () => {
  it("POST /ai/purpose-proposals を呼び、ジョブ完了を待って結果を返す", async () => {
    vi.mocked(api.post).mockResolvedValue({ job_id: "job-1", poll_after_ms: 1500 });
    vi.mocked(waitForJob).mockResolvedValue({
      proposals: [
        { direction: "SELF", label: "自分の納得を軸に", statement: "…でありたい。" },
        { direction: "OTHERS", label: "まわりの人とともに", statement: "…でありたい。" },
        { direction: "SOCIETY", label: "もっと広く", statement: "…していきたい。" },
      ],
      safety_flag: false,
    });

    const result = await generatePurposeProposals(choices, messages);

    expect(api.post).toHaveBeenCalledWith(
      "/ai/purpose-proposals",
      { choices, messages },
      { signal: undefined },
    );
    expect(waitForJob).toHaveBeenCalledWith("job-1", 1500, undefined);
    expect(result.proposals).toHaveLength(3);
  });

  it("AbortSignalをジョブ作成・ポーリングの両方に渡す", async () => {
    vi.mocked(api.post).mockResolvedValue({ job_id: "job-1", poll_after_ms: 1500 });
    vi.mocked(waitForJob).mockResolvedValue({ proposals: [], safety_flag: false });
    const controller = new AbortController();

    await generatePurposeProposals(choices, messages, controller.signal);

    expect(api.post).toHaveBeenCalledWith(expect.any(String), expect.any(Object), {
      signal: controller.signal,
    });
    expect(waitForJob).toHaveBeenCalledWith("job-1", 1500, controller.signal);
  });
});
