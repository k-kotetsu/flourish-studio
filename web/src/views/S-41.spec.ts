import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { getHome, type HomeResponse } from "../api/home";
import { useThemeStore } from "../stores/theme";
import S41View from "./S-41.vue";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push }),
}));
vi.mock("../api/home", () => ({
  getHome: vi.fn(),
}));

const homeResponse: HomeResponse = {
  purpose: { statement: "静かに機嫌よく生きる", version: 1 },
  areas: [
    { area: "CAREER", status: "EMPTY" },
    { area: "FINANCIAL", status: "EMPTY" },
    { area: "PHYSICAL", status: "EMPTY" },
    { area: "SOCIAL", status: "EMPTY" },
  ],
  reflection_available: false,
  theme_preference: "DARK",
};

describe("S-41", () => {
  beforeEach(() => {
    push.mockReset();
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    setActivePinia(createPinia());
  });

  it("ヘッダー右端にテーマ切替トグルを置く", async () => {
    vi.mocked(getHome).mockResolvedValue(homeResponse);
    const wrapper = mount(S41View);
    await flushPromises();

    expect(wrapper.find(".theme-toggle").exists()).toBe(true);
  });

  it("GET /homeが返すtheme_preferenceをテーマストアへ反映する（端末をまたいで一致させる）", async () => {
    vi.mocked(getHome).mockResolvedValue(homeResponse);
    mount(S41View);
    await flushPromises();

    const themeStore = useThemeStore();
    expect(themeStore.mode).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});

function flushPromises(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}
