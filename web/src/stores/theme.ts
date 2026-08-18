import { defineStore } from "pinia";
import { updateThemePreference, type ThemePreference } from "../api/me";

/**
 * 07_デザイン原則 3.1〜3.2。
 * 既定はOS追従（auto）。手動選択はOS設定より優先し、循環順は auto → light → dark → auto。
 * 選択はアカウントに紐づけて保存する（P4-9、`PATCH /me`）。トグルUI自体は`ThemeToggle.vue`。
 */
export type ThemeMode = "auto" | "light" | "dark";

const STORAGE_KEY = "flourish-theme";
const CYCLE: readonly ThemeMode[] = ["auto", "light", "dark"];

const MODE_TO_PREFERENCE: Record<ThemeMode, ThemePreference> = {
  auto: "AUTO",
  light: "LIGHT",
  dark: "DARK",
};

const PREFERENCE_TO_MODE: Record<ThemePreference, ThemeMode> = {
  AUTO: "auto",
  LIGHT: "light",
  DARK: "dark",
};

function readStoredMode(): ThemeMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark") {
      return stored;
    }
  } catch {
    // localStorageが使えない環境（プライベートモード等）は自動追従にフォールバックする
  }
  return "auto";
}

function applyMode(mode: ThemeMode): void {
  const root = document.documentElement;
  if (mode === "auto") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", mode);
  }
}

export const useThemeStore = defineStore("theme", {
  state: () => ({
    mode: readStoredMode() as ThemeMode,
  }),
  actions: {
    init(): void {
      applyMode(this.mode);
    },
    setMode(mode: ThemeMode): void {
      this.mode = mode;
      applyMode(mode);
      try {
        if (mode === "auto") {
          localStorage.removeItem(STORAGE_KEY);
        } else {
          localStorage.setItem(STORAGE_KEY, mode);
        }
      } catch {
        // 保存できなくても表示上の切り替えは成立させる
      }
    },
    /**
     * `GET /home`（P4-8）が返すアカウントの`theme_preference`を反映する。
     * サーバー側の値を優先する（3.1「端末をまたいで一致させる」）ため、`PATCH`は呼ばない。
     */
    syncFromServer(preference: ThemePreference): void {
      this.setMode(PREFERENCE_TO_MODE[preference]);
    },
    /** ホーム（S-41）のトグルが呼ぶ。即座に画面へ反映し、アカウントへの保存は非同期で行う。 */
    cycle(): void {
      const next = CYCLE[(CYCLE.indexOf(this.mode) + 1) % CYCLE.length];
      this.setMode(next);
      updateThemePreference(MODE_TO_PREFERENCE[next]).catch(() => {
        // 画面には既に適用済み。保存に失敗しても操作をブロックしない。次回GET /homeで再同期される
      });
    },
  },
});
