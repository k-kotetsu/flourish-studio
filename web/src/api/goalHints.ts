/**
 * `POST /ai/goal-hints`(同期)。09_API設計5.10、10_AIプロンプト設計4.7、S-56。
 * ジョブを作らない同期呼び出しで、目標候補を3件返す。確定済みの「ありたい姿」はリクエストに
 * 含めない(サーバーが`PURPOSE#CURRENT`から読む。`streamAreaDialogue`と同じ判断)。
 * 失敗時は呼び出し側(`ApiError`をそのまま伝播)が画面内にエラーを出すだけで、
 * 進行は止めない(候補が出なくてもユーザーは自分で書ける)。
 */
import type { AreaSlug } from "./areaDialogue";
import { api } from "./client";

interface GoalHintsResponse {
  hints: string[];
}

export async function generateGoalHints(
  area: AreaSlug,
  idealState: string,
  existingGoals: string[],
  signal?: AbortSignal,
): Promise<string[]> {
  const response = await api.post<GoalHintsResponse>(
    "/ai/goal-hints",
    { area, ideal_state: idealState, existing_goals: existingGoals },
    { signal },
  );
  return response.hints;
}
