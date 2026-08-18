import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { api } from "../api/client";
import { useThemeStore } from "../stores/theme";
import ThemeToggle from "./ThemeToggle.vue";

vi.mock("../api/client", () => ({
  api: { patch: vi.fn() },
}));

describe("ThemeToggle", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    setActivePinia(createPinia());
    vi.mocked(api.patch).mockResolvedValue({ theme_preference: "AUTO" });
  });

  it("既定（自動）ではラベル「システムに追従」を表示する", () => {
    const wrapper = mount(ThemeToggle);
    expect(wrapper.text()).toContain("システムに追従");
  });

  it("タップのたびに 自動 → ライト → ダーク → 自動 と表示が切り替わり、PATCH /meへ保存する", async () => {
    const wrapper = mount(ThemeToggle);
    const store = useThemeStore();

    await wrapper.find("button").trigger("click");
    expect(store.mode).toBe("light");
    expect(wrapper.text()).toContain("ライト固定");
    expect(api.patch).toHaveBeenCalledWith("/me", { theme_preference: "LIGHT" });

    await wrapper.find("button").trigger("click");
    expect(store.mode).toBe("dark");
    expect(wrapper.text()).toContain("ダーク固定");
    expect(api.patch).toHaveBeenCalledWith("/me", { theme_preference: "DARK" });

    await wrapper.find("button").trigger("click");
    expect(store.mode).toBe("auto");
    expect(wrapper.text()).toContain("システムに追従");
    expect(api.patch).toHaveBeenCalledWith("/me", { theme_preference: "AUTO" });
  });

  it("保存に失敗しても画面上の状態は切り替わったまま残す", async () => {
    vi.mocked(api.patch).mockRejectedValue(new Error("network down"));
    const wrapper = mount(ThemeToggle);
    const store = useThemeStore();

    await wrapper.find("button").trigger("click");
    await Promise.resolve();

    expect(store.mode).toBe("light");
    expect(wrapper.text()).toContain("ライト固定");
  });
});
