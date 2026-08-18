import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { updateThemePreference } from "../api/me";
import { useThemeStore } from "./theme";

vi.mock("../api/me", () => ({
  updateThemePreference: vi.fn(),
}));

describe("useThemeStore", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    setActivePinia(createPinia());
    vi.mocked(updateThemePreference).mockReset().mockResolvedValue({ theme_preference: "AUTO" });
  });

  it("永続化された選択がなければ auto から始まる", () => {
    const store = useThemeStore();
    expect(store.mode).toBe("auto");
  });

  it("auto では data-theme 属性を付けない（OS追従に委ねる）", () => {
    const store = useThemeStore();
    store.init();
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
  });

  it("setMode(light/dark) は data-theme を即座に反映し、localStorageへ保存する", () => {
    const store = useThemeStore();

    store.setMode("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(localStorage.getItem("flourish-theme")).toBe("dark");

    store.setMode("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(localStorage.getItem("flourish-theme")).toBe("light");
  });

  it("auto に戻すと属性とlocalStorageの両方をクリアする", () => {
    const store = useThemeStore();
    store.setMode("dark");

    store.setMode("auto");
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
    expect(localStorage.getItem("flourish-theme")).toBeNull();
  });

  it("cycle() は auto → light → dark → auto の順で循環する", () => {
    const store = useThemeStore();

    expect(store.mode).toBe("auto");
    store.cycle();
    expect(store.mode).toBe("light");
    store.cycle();
    expect(store.mode).toBe("dark");
    store.cycle();
    expect(store.mode).toBe("auto");
  });

  it("cycle() は画面へ即座に反映したうえで、アカウントへ保存する（PATCH /me）", () => {
    const store = useThemeStore();

    store.cycle();
    expect(updateThemePreference).toHaveBeenCalledWith("LIGHT");

    store.cycle();
    expect(updateThemePreference).toHaveBeenCalledWith("DARK");
  });

  it("保存に失敗しても画面上の状態はそのまま残る", async () => {
    vi.mocked(updateThemePreference).mockRejectedValue(new Error("network down"));
    const store = useThemeStore();

    store.cycle();
    await Promise.resolve();

    expect(store.mode).toBe("light");
  });

  it("既存の永続化された選択を初期状態に反映する", () => {
    localStorage.setItem("flourish-theme", "dark");
    const store = useThemeStore();
    expect(store.mode).toBe("dark");
  });

  it("syncFromServer() はアカウントの選択（サーバー値）を優先し、PATCHは呼ばない", () => {
    localStorage.setItem("flourish-theme", "dark");
    const store = useThemeStore();

    store.syncFromServer("LIGHT");

    expect(store.mode).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(updateThemePreference).not.toHaveBeenCalled();
  });
});
