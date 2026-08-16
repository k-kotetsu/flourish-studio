import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import CheckboxChoiceSelector from "./CheckboxChoiceSelector.vue";

const choices = [
  { code: "HELPED_SOMEONE", label: "誰かの役に立てたと感じたとき" },
  { code: "NEW_ABILITY", label: "新しいことができるようになったとき" },
  { code: "SELF_DETERMINED", label: "自分で決められたと感じたとき" },
];

describe("CheckboxChoiceSelector", () => {
  it("選択肢が全文で縦に並ぶ", () => {
    const wrapper = mount(CheckboxChoiceSelector, {
      props: { modelValue: [], choices, labelledBy: "q2", name: "q2" },
    });

    const options = wrapper.findAll(".checkbox-choice-selector__option");
    expect(options).toHaveLength(3);
    expect(options[1]?.text()).toBe("新しいことができるようになったとき");
  });

  it("選択済みの選択肢に見た目のクラスが付く", () => {
    const wrapper = mount(CheckboxChoiceSelector, {
      props: { modelValue: ["NEW_ABILITY"], choices, labelledBy: "q2", name: "q2" },
    });

    const options = wrapper.findAll(".checkbox-choice-selector__option");
    expect(options[1]?.classes()).toContain("checkbox-choice-selector__option--selected");
    expect(options[0]?.classes()).not.toContain("checkbox-choice-selector__option--selected");
  });

  it("未選択のチェックボックスを選ぶと追加されたmodelValueが発火する", async () => {
    const wrapper = mount(CheckboxChoiceSelector, {
      props: { modelValue: ["HELPED_SOMEONE"], choices, labelledBy: "q2", name: "q2" },
    });

    await wrapper.findAll(".checkbox-choice-selector__input")[1]?.setValue(true);

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([["HELPED_SOMEONE", "NEW_ABILITY"]]);
  });

  it("選択済みのチェックボックスを外すとmodelValueから消える", async () => {
    const wrapper = mount(CheckboxChoiceSelector, {
      props: { modelValue: ["HELPED_SOMEONE", "NEW_ABILITY"], choices, labelledBy: "q2", name: "q2" },
    });

    await wrapper.findAll(".checkbox-choice-selector__input")[0]?.setValue(false);

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([["NEW_ABILITY"]]);
  });

  it("上限なく複数選択できる", async () => {
    const wrapper = mount(CheckboxChoiceSelector, {
      props: { modelValue: ["HELPED_SOMEONE", "NEW_ABILITY"], choices, labelledBy: "q2", name: "q2" },
    });

    await wrapper.findAll(".checkbox-choice-selector__input")[2]?.setValue(true);

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([["HELPED_SOMEONE", "NEW_ABILITY", "SELF_DETERMINED"]]);
  });
});
