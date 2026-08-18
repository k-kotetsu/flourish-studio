/**
 * `PATCH /me`。09_API設計4章、08_データモデル6.1。テーマ設定をアカウントに保存する。
 * `GET /me`はP4-8の`GET /home`が`theme_preference`をまとめて返すため、フロントからは呼ばない。
 */
import { api } from "./client";

export type ThemePreference = "AUTO" | "LIGHT" | "DARK";

export interface MeResponse {
  theme_preference: ThemePreference;
}

export function updateThemePreference(themePreference: ThemePreference): Promise<MeResponse> {
  return api.patch<MeResponse>("/me", { theme_preference: themePreference });
}
