/**
 * `GET /reflections/context`、`POST /reflections` → ジョブ完了待ち、`GET /reflections/{id}`。
 * 09_API設計5.13〜5.15、04_画面設計S-61〜S-63、10_AIプロンプト設計4.8。
 * 識別子は`goal_key`のみを使う(`goal_id`はVersion 0.2で廃止済み、08_データモデル5.3)。
 */
import type { AreaSlug } from "./areaDialogue";
import type { ReflectionStatusAnswer } from "../stores/reflectionAnswers";
import { api } from "./client";
import { waitForJob } from "./jobs";

export interface ReflectionGoal {
  goal_key: string;
  area: AreaSlug;
  body: string;
}

export interface ReflectionContextResponse {
  goals: ReflectionGoal[];
}

export function getReflectionContext(): Promise<ReflectionContextResponse> {
  return api.get<ReflectionContextResponse>("/reflections/context");
}

export interface ReflectionResult {
  looking_back: string;
  insight: string;
  next_step: string;
  safety_flag: boolean;
  generated_at: string;
  answered_at: string;
}

interface CreateJobResponse {
  job_id: string;
  poll_after_ms: number;
}

interface ReflectionJobResult {
  reflection_id: string;
}

export async function generateReflection(
  statuses: ReflectionStatusAnswer[],
  note: string | null,
  signal?: AbortSignal,
): Promise<ReflectionResult> {
  const { job_id: jobId, poll_after_ms: pollAfterMs } = await api.post<CreateJobResponse>(
    "/reflections",
    { statuses, note },
    { signal },
  );
  const { reflection_id: reflectionId } = await waitForJob<ReflectionJobResult>(
    jobId,
    pollAfterMs,
    signal,
  );
  return api.get<ReflectionResult>(`/reflections/${reflectionId}`, { signal });
}
