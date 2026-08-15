/**
 * `POST /ai/assessment-questions` → ジョブ完了待ち。09_API設計5.2、S-13。
 * 選択式24問の回答から、自由記述8問の問い文を生成する(保存しない)。
 */
import type { Area } from "../domain/questions";
import type { ScaleAnswer } from "../stores/assessmentAnswers";
import { api } from "./client";
import { waitForJob } from "./jobs";

export type QuestionSlot = "SATISFIED" | "CONCERN";

export interface AssessmentQuestion {
  area: Area;
  slot: QuestionSlot;
  target_item_code: string;
  text: string;
}

interface AssessmentQuestionsResult {
  questions: AssessmentQuestion[];
}

interface CreateJobResponse {
  job_id: string;
  poll_after_ms: number;
}

export async function generateAssessmentQuestions(
  scaleAnswers: ScaleAnswer[],
  questionSetVersion: string,
  signal?: AbortSignal,
): Promise<AssessmentQuestion[]> {
  const { job_id: jobId, poll_after_ms: pollAfterMs } = await api.post<CreateJobResponse>(
    "/ai/assessment-questions",
    { scale_answers: scaleAnswers, question_set_version: questionSetVersion },
    { signal },
  );
  const result = await waitForJob<AssessmentQuestionsResult>(jobId, pollAfterMs, signal);
  return result.questions;
}
