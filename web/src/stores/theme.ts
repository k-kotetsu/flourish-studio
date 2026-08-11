import { defineStore } from "pinia";

/**
 * 07_デザイン原則 3.1〜3.2。
 * 既定はOS追従（auto）。手動選択はOS設定より優先し、循環順は auto → light → dark → auto。
 * トグルUI自体はP4-9で実装する。ここではその土台となる状態管理のみを持つ。
 */
export type ThemeMode = "auto" | "light" | "dark";

const STORAGE_KEY = "flourish-theme";
const CYCLE: readonly ThemeMode[] = ["auto", "light", "dark"];

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
    cycle(): void {
      const next = CYCLE[(CYCLE.indexOf(this.mode) + 1) % CYCLE.length];
      this.setMode(next);
    },
  },
});
