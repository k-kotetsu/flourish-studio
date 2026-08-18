/**
 * `POST /area-plans`。09_API設計5.11、08_データモデル4.2〜4.4、S-56の確定。
 * 選択式回答(S-51)・対話全文(S-52)・選ばれた案(S-54)・編集後の理想状態(S-55)・目標1〜3個を
 * まとめて送り、ここではじめて保存する(`purposes.ts` `createPurpose`と同じ考え方)。
 */
import type { AreaDialogueChoice, AreaDialogueMessage, AreaSlug } from "./areaDialogue";
import type { AreaDirection } from "./areaProposals";
import { api } from "./client";

export interface AreaPlanGoalIn {
  body: string;
  sort_order: number;
}

export interface AreaPlanGoal {
  goal_key: string;
  body: string;
  sort_order: number;
}

export interface AreaPlanResponse {
  version: number;
  area: AreaSlug;
  ideal_state: string;
  selected_direction: AreaDirection;
  selected_label: string;
  goals: AreaPlanGoal[];
  created_at: string;
}

interface CreateAreaPlanRequest {
  area: AreaSlug;
  choices: AreaDialogueChoice[];
  messages: AreaDialogueMessage[];
  selected_direction: AreaDirection;
  selected_label: string;
  original_ideal_state: string;
  ideal_state: string;
  goals: AreaPlanGoalIn[];
}

export async function createAreaPlan(body: CreateAreaPlanRequest): Promise<AreaPlanResponse> {
  return api.post<AreaPlanResponse>("/area-plans", body);
}
