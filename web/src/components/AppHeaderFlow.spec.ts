import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import AppHeaderFlow from "./AppHeaderFlow.vue";

describe("AppHeaderFlow", () => {
  it("既定（back）では「‹ 戻る」を表示し、押すと back を発火する", async () => {
    const wrapper = mount(AppHeaderFlow, {
      props: { title: "現在地レポート", percent: 17 },
    });
    expect(wrapper.text()).toContain("‹ 戻る");
    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("back")).toHaveLength(1);
  });

  it("leftAction=cancel では「× 中断」を表示し、押すと cancel を発火する", async () => {
    const wrapper = mount(AppHeaderFlow, {
      props: { title: "現在地レポート", percent: 0, leftAction: "cancel" },
    });
    expect(wrapper.text()).toContain("× 中断");
    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("cancel")).toHaveLength(1);
  });

  it("leftAction=none（生成中画面）ではボタンを置かない", () => {
    const wrapper = mount(AppHeaderFlow, {
      props: { title: "現在地レポート", percent: 67, leftAction: "none" },
    });
    expect(wrapper.find("button").exists()).toBe(false);
  });

  it("step が無ければステップ番号を表示しない（生成中画面はステップに数えない）", () => {
    const wrapper = mount(AppHeaderFlow, {
      props: { title: "現在地レポート", percent: 67, leftAction: "none" },
    });
    expect(wrapper.find(".app-header-flow__step").exists()).toBe(false);
  });

  it("step があれば表示する", () => {
    const wrapper = mount(AppHeaderFlow, {
      props: { title: "現在地レポート", percent: 17, step: "1 / 6" },
    });
    expect(wrapper.text()).toContain("1 / 6");
  });

  it("プログレスバーに percent を渡す", () => {
    const wrapper = mount(AppHeaderFlow, {
      props: { title: "現在地レポート", percent: 83 },
    });
    expect(wrapper.find('[role="progressbar"]').attributes("aria-valuenow")).toBe(
      "83",
    );
  });
});
