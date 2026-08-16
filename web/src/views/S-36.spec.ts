import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import S36View from "./S-36.vue";
import { getCurrentPurpose } from "../api/purposes";
import { ApiError } from "../api/client";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push }),
}));
vi.mock("../api/purposes", () => ({
  getCurrentPurpose: vi.fn(),
}));

const PURPOSE = {
  version: 1,
  statement: "自分で選んだと言えることを積み重ねて生きていきたい。",
  selected_direction: "SELF" as const,
  selected_label: "自分の納得を軸に",
  created_at: "2026-08-07T05:00:00Z",
};

afterEach(() => {
  push.mockReset();
  vi.mocked(getCurrentPurpose).mockReset();
});

describe("S-36", () => {
  it("取得したありたい姿と作成日付を表示する", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);

    const wrapper = mount(S36View);
    await flushPromises();

    expect(wrapper.text()).toContain(PURPOSE.statement);
    expect(wrapper.text()).toContain("2026年8月7日に作成");
  });

  it("取得に失敗したらエラーを表示する", async () => {
    vi.mocked(getCurrentPurpose).mockRejectedValue(
      new ApiError(404, "PURPOSE_NOT_FOUND", "purpose has not been created yet"),
    );

    const wrapper = mount(S36View);
    await flushPromises();

    expect(wrapper.text()).toContain("うまくいきませんでした");
  });

  it("「編集する」でS-37へ遷移する", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const wrapper = mount(S36View);
    await flushPromises();

    await wrapper.find("button.app-button--secondary").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-37");
  });

  it("「AIと話して作り直す」でS-31へ遷移する", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const wrapper = mount(S36View);
    await flushPromises();

    await wrapper.find(".s36__retry").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-31");
  });

  it("‹戻るでS-41へ遷移する", async () => {
    vi.mocked(getCurrentPurpose).mockResolvedValue(PURPOSE);
    const wrapper = mount(S36View);
    await flushPromises();

    await wrapper.find(".app-header-single__nav").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-41");
  });
});
