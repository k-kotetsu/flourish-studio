/**
 * `POST /assessments` → ジョブ完了待ち → `GET /assessments/{id}`。09_API設計5.3〜5.4、S-15→S-16。
 * 選択式24問・自由記述8問から現在地レポートを生成し、そのまま結果一式を取得する。
 * S-16は状態バリエーションを持たない(06_ワイヤーフレーム3章)ため、失敗はこの一連の呼び出しの
 * 中(S-15の生成中画面)で使い切り、S-16には成功した結果だけを渡す。
 */
import type { Area } from "../domain/questions";
import type { GrowthStage } from "../domain/growthStage";
import type { FreeTextAnswer } from "../stores/freeTextAnswers";
import type { ScaleAnswer } from "../stores/assessmentAnswers";
import { api } from "./client";
import { waitForJob } from "./jobs";

export interface AssessmentAreaResult {
  area: Area;
  satisfied_text: string;
  concern_text: string;
  advice_text: string;
}

export interface AssessmentResult {
  nickname: string;
  articulation_stage: GrowthStage;
  commitment_stage: GrowthStage;
  commitment_score: number;
  safety_flag: boolean;
  areas: AssessmentAreaResult[];
  generated_at: string;
}

interface CreateJobResponse {
  job_id: string;
  poll_after_ms: number;
}

interface AssessmentJobResult {
  assessment_id: string;
}

export async function generateAssessmentReport(
  scaleAnswers: ScaleAnswer[],
  freeTextAnswers: FreeTextAnswer[],
  questionSetVersion: string,
  signal?: AbortSignal,
): Promise<AssessmentResult> {
  const { job_id: jobId, poll_after_ms: pollAfterMs } = await api.post<CreateJobResponse>(
    "/assessments",
    {
      scale_answers: scaleAnswers,
      free_text_answers: freeTextAnswers,
      question_set_version: questionSetVersion,
    },
    { signal },
  );
  const { assessment_id: assessmentId } = await waitForJob<AssessmentJobResult>(
    jobId,
    pollAfterMs,
    signal,
  );
  return api.get<AssessmentResult>(`/assessments/${assessmentId}`, { signal });
}
