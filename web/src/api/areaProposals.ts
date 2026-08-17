/**
 * `POST /ai/area-proposals` → ジョブ完了待ち。09_API設計6章、10_AIプロンプト設計4.6、S-53。
 * 対象領域・S-51の選択式回答・S-52の対話全文から、理想状態の3案を生成する(保存しない)。
 * 確定済みの「ありたい姿」はリクエストに含めない(サーバーが`PURPOSE#CURRENT`から読む。
 * `streamAreaDialogue`と同じ判断)。
 */
import type { AreaDialogueChoice, AreaDialogueMessage, AreaSlug } from "./areaDialogue";
import { api } from "./client";
import { waitForJob } from "./jobs";

export type AreaDirection = "DEEPEN" | "CHANGE" | "EXPAND";

export interface AreaProposal {
  direction: AreaDirection;
  label: string;
  ideal_state: string;
}

interface AreaProposalsResult {
  proposals: AreaProposal[];
  safety_flag: boolean;
}

interface CreateJobResponse {
  job_id: string;
  poll_after_ms: number;
}

export async function generateAreaProposals(
  area: AreaSlug,
  choices: AreaDialogueChoice[],
  messages: AreaDialogueMessage[],
  signal?: AbortSignal,
): Promise<AreaProposalsResult> {
  const { job_id: jobId, poll_after_ms: pollAfterMs } = await api.post<CreateJobResponse>(
    "/ai/area-proposals",
    { area, choices, messages },
    { signal },
  );
  return waitForJob<AreaProposalsResult>(jobId, pollAfterMs, signal);
}
