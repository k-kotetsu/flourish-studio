import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import StackedChoiceSelector from "./StackedChoiceSelector.vue";

const choices = [
  { score: 0, label: "まだこれからのところ" },
  { score: 1, label: "あまり動けていない" },
  { score: 2, label: "動けている時と、そうでない時がある" },
  { score: 3, label: "少し動けている" },
  { score: 4, label: "しっかり動けている" },
];

describe("StackedChoiceSelector", () => {
  it("5つの選択肢が全文で縦に並ぶ", () => {
    const wrapper = mount(StackedChoiceSelector, {
      props: { modelValue: null, choices, labelledBy: "q6", name: "q6" },
    });

    const options = wrapper.findAll(".stacked-choice-selector__option");
    expect(options).toHaveLength(5);
    expect(options[2]?.text()).toBe("動けている時と、そうでない時がある");
  });

  it("選択済みの選択肢に見た目のクラスが付く", () => {
    const wrapper = mount(StackedChoiceSelector, {
      props: { modelValue: 4, choices, labelledBy: "q6", name: "q6" },
    });

    const options = wrapper.findAll(".stacked-choice-selector__option");
    expect(options[4]?.classes()).toContain("stacked-choice-selector__option--selected");
    expect(options[0]?.classes()).not.toContain("stacked-choice-selector__option--selected");
  });

  it("選択肢を選ぶと update:modelValue がスコアつきで発火する", async () => {
    const wrapper = mount(StackedChoiceSelector, {
      props: { modelValue: null, choices, labelledBy: "q6", name: "q6" },
    });

    await wrapper.findAll(".stacked-choice-selector__input")[4]?.setValue();

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([4]);
  });
});
