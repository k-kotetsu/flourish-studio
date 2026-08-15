import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import S11View from "./S-11.vue";
import { createGuestSession } from "../api/guestSessions";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push }),
}));
vi.mock("../api/guestSessions", () => ({
  createGuestSession: vi.fn(),
}));

afterEach(() => {
  vi.mocked(createGuestSession).mockReset();
  push.mockReset();
});

describe("S-11", () => {
  it("画面到達時にゲストセッションを発行する", async () => {
    vi.mocked(createGuestSession).mockResolvedValue(undefined);

    mount(S11View);
    await flushPromises();

    expect(createGuestSession).toHaveBeenCalledOnce();
  });

  it("発行が終わるまで「はじめる」を押せない", async () => {
    let resolveCreate!: () => void;
    vi.mocked(createGuestSession).mockReturnValue(
      new Promise((resolve) => {
        resolveCreate = () => resolve(undefined);
      }),
    );

    const wrapper = mount(S11View);
    expect(wrapper.find(".s11__cta button:not([disabled])").exists()).toBe(false);

    resolveCreate();
    await flushPromises();

    expect(wrapper.find(".s11__cta button:not([disabled])").exists()).toBe(true);
  });

  it("発行できたら「はじめる」で次の画面へ遷移する", async () => {
    vi.mocked(createGuestSession).mockResolvedValue(undefined);
    const wrapper = mount(S11View);
    await flushPromises();

    await wrapper.find(".s11__cta button").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-12");
  });

  it("発行に失敗したらエラーを表示し、自動では再試行しない", async () => {
    vi.mocked(createGuestSession).mockRejectedValueOnce(new Error("network down"));

    const wrapper = mount(S11View);
    await flushPromises();

    expect(createGuestSession).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain("うまく始められませんでした");
    expect(wrapper.text()).toContain("もう一度試す");
  });

  it("「もう一度試す」を押したときだけ再試行する", async () => {
    vi.mocked(createGuestSession)
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValueOnce(undefined);

    const wrapper = mount(S11View);
    await flushPromises();
    expect(createGuestSession).toHaveBeenCalledOnce();

    await wrapper.find(".s11__cta button").trigger("click");
    await flushPromises();

    expect(createGuestSession).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).not.toContain("うまく始められませんでした");
  });
});
