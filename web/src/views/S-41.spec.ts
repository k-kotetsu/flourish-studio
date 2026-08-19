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

  it("目標0個ではWeekly Reflection導線を無効状態で表示し、消さずに理由を添える", async () => {
    vi.mocked(getHome).mockResolvedValue({ ...homeResponse, reflection_available: false });
    const wrapper = mount(S41View);
    await flushPromises();

    const button = wrapper.find("button.app-button");
    expect(button.exists()).toBe(true);
    expect(button.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("目標を1つ作ると振り返れるようになります");

    await button.trigger("click");
    expect(push).not.toHaveBeenCalled();
  });

  it("目標1個以上ではWeekly Reflection導線を有効にし、理由は添えずタップでS-61へ遷移する", async () => {
    vi.mocked(getHome).mockResolvedValue({ ...homeResponse, reflection_available: true });
    const wrapper = mount(S41View);
    await flushPromises();

    const button = wrapper.find("button.app-button");
    expect(button.attributes("disabled")).toBeUndefined();
    expect(wrapper.text()).not.toContain("目標を1つ作ると振り返れるようになります");

    await button.trigger("click");
    expect(push).toHaveBeenCalledWith("/s-61");
  });
});

function flushPromises(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}
