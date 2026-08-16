/**
 * `POST /ai/purpose-proposals` → ジョブ完了待ち。09_API設計5.7、S-33。
 * 選択式3問の回答と対話全文から、ありたい姿の3案を生成する(保存しない)。
 */
import { api } from "./client";
import { waitForJob } from "./jobs";
import type { PurposeDialogueChoice, PurposeDialogueMessage } from "./purposeDialogue";

export type PurposeDirection = "SELF" | "OTHERS" | "SOCIETY";

export interface PurposeProposal {
  direction: PurposeDirection;
  label: string;
  statement: string;
}

interface PurposeProposalsResult {
  proposals: PurposeProposal[];
  safety_flag: boolean;
}

interface CreateJobResponse {
  job_id: string;
  poll_after_ms: number;
}

export async function generatePurposeProposals(
  choices: PurposeDialogueChoice[],
  messages: PurposeDialogueMessage[],
  signal?: AbortSignal,
): Promise<PurposeProposalsResult> {
  const { job_id: jobId, poll_after_ms: pollAfterMs } = await api.post<CreateJobResponse>(
    "/ai/purpose-proposals",
    { choices, messages },
    { signal },
  );
  return waitForJob<PurposeProposalsResult>(jobId, pollAfterMs, signal);
}
