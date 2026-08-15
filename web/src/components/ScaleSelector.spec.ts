import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import ScaleSelector from "./ScaleSelector.vue";

const choices = [
  { score: 0, label: "満たされていない" },
  { score: 1, label: "あまり満たされていない" },
  { score: 2, label: "どちらとも言えない" },
  { score: 3, label: "まあ満たされている" },
  { score: 4, label: "満たされている" },
];

describe("ScaleSelector", () => {
  it("5段階すべてが描画される", () => {
    const wrapper = mount(ScaleSelector, {
      props: { modelValue: null, choices, labelledBy: "q1", name: "q1" },
    });

    expect(wrapper.findAll(".scale-selector__cell")).toHaveLength(5);
  });

  it("両端にのみラベルを表示する", () => {
    const wrapper = mount(ScaleSelector, {
      props: { modelValue: null, choices, labelledBy: "q1", name: "q1" },
    });

    const anchors = wrapper.findAll(".scale-selector__anchors span");
    expect(anchors).toHaveLength(2);
    expect(anchors[0]?.text()).toBe("満たされていない");
    expect(anchors[1]?.text()).toBe("満たされている");
  });

  it("選択済みのセルに見た目のクラスが付く", () => {
    const wrapper = mount(ScaleSelector, {
      props: { modelValue: 3, choices, labelledBy: "q1", name: "q1" },
    });

    const cells = wrapper.findAll(".scale-selector__cell");
    expect(cells[3]?.classes()).toContain("scale-selector__cell--selected");
    expect(cells[0]?.classes()).not.toContain("scale-selector__cell--selected");
  });

  it("セルを選ぶと update:modelValue がスコアつきで発火する", async () => {
    const wrapper = mount(ScaleSelector, {
      props: { modelValue: null, choices, labelledBy: "q1", name: "q1" },
    });

    await wrapper.findAll(".scale-selector__input")[2]?.setValue();

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([2]);
  });
});
