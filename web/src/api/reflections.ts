/**
 * `GET /reflections/context`。09_API設計5.13、04_画面設計S-61。
 * 回答対象の目標一覧を取得する画面専用エンドポイント。目標が0件でも空配列(200)で返る。
 * 識別子は`goal_key`のみを使う(`goal_id`はVersion 0.2で廃止済み、08_データモデル5.3)。
 */
import type { AreaSlug } from "./areaDialogue";
import { api } from "./client";

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
