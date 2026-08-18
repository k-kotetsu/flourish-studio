/**
 * `GET /home`。09_API設計5.9、04_画面設計S-41。ありたい姿・4領域・振り返り導線の可否・
 * テーマ設定を1回のリクエストでまとめて返す画面専用エンドポイント。
 */
import type { AreaSlug } from "./areaDialogue";
import { api } from "./client";

export interface HomePurpose {
  statement: string;
  version: number;
}

export interface HomeAreaEmpty {
  area: AreaSlug;
  status: "EMPTY";
}

export interface HomeAreaCreated {
  area: AreaSlug;
  status: "CREATED";
  ideal_state_summary: string;
  goal_count: number;
}

export type HomeArea = HomeAreaEmpty | HomeAreaCreated;

export interface HomeResponse {
  purpose: HomePurpose | null;
  areas: HomeArea[];
  reflection_available: boolean;
  theme_preference: "AUTO" | "LIGHT" | "DARK";
}

export function getHome(): Promise<HomeResponse> {
  return api.get<HomeResponse>("/home");
}
