/**
 * `POST /area-plans` ／ `GET`/`PUT /area-plans/{area}`。09_API設計5.11・5.12、
 * 08_データモデル4.2〜4.5、S-56の確定／S-57の閲覧／S-58の編集。
 * `POST`は選択式回答(S-51)・対話全文(S-52)・選ばれた案(S-54)・編集後の理想状態(S-55)・
 * 目標1〜3個をまとめて送り、ここではじめて保存する(`purposes.ts` `createPurpose`と同じ考え方)。
 * `GET`/`PUT`は保存済みの領域の計画を閲覧・編集する(`PUT`は上書きではなく新しいversionを作る。
 * `purposes.ts`の`getCurrentPurpose`/`updateCurrentPurpose`と同じ考え方)。
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

export function getAreaPlan(area: AreaSlug): Promise<AreaPlanResponse> {
  return api.get<AreaPlanResponse>(`/area-plans/${area}`);
}

export interface AreaPlanGoalUpdateIn {
  goal_key?: string;
  body: string;
  sort_order: number;
}

interface UpdateAreaPlanRequest {
  ideal_state: string;
  goals: AreaPlanGoalUpdateIn[];
}

export function updateAreaPlan(
  area: AreaSlug,
  body: UpdateAreaPlanRequest,
): Promise<AreaPlanResponse> {
  return api.put<AreaPlanResponse>(`/area-plans/${area}`, body);
}
