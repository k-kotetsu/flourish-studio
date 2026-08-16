import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import ChipMultiSelect from "./ChipMultiSelect.vue";

const choices = [
  { code: "GROWTH", label: "成長" },
  { code: "STABILITY", label: "安定" },
  { code: "FREEDOM", label: "自由" },
  { code: "CONNECTION", label: "つながり" },
];

describe("ChipMultiSelect", () => {
  it("選択肢がすべてチップとして並ぶ", () => {
    const wrapper = mount(ChipMultiSelect, {
      props: { modelValue: [], choices, max: 3, labelledBy: "q1" },
    });

    const chips = wrapper.findAll(".chip-multi-select__chip");
    expect(chips).toHaveLength(4);
    expect(chips[0]?.text()).toBe("成長");
  });

  it("選択済みのチップに見た目のクラスが付く", () => {
    const wrapper = mount(ChipMultiSelect, {
      props: { modelValue: ["STABILITY"], choices, max: 3, labelledBy: "q1" },
    });

    const chips = wrapper.findAll(".chip-multi-select__chip");
    expect(chips[1]?.classes()).toContain("chip-multi-select__chip--selected");
    expect(chips[0]?.classes()).not.toContain("chip-multi-select__chip--selected");
  });

  it("未選択のチップを押すと追加されたmodelValueが発火する", async () => {
    const wrapper = mount(ChipMultiSelect, {
      props: { modelValue: ["GROWTH"], choices, max: 3, labelledBy: "q1" },
    });

    await wrapper.findAll(".chip-multi-select__chip")[1]?.trigger("click");

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([["GROWTH", "STABILITY"]]);
  });

  it("選択済みのチップを押すと外れたmodelValueが発火する", async () => {
    const wrapper = mount(ChipMultiSelect, {
      props: { modelValue: ["GROWTH", "STABILITY"], choices, max: 3, labelledBy: "q1" },
    });

    await wrapper.findAll(".chip-multi-select__chip")[0]?.trigger("click");

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([["STABILITY"]]);
  });

  it("上限に達すると未選択のチップが無効になり、押しても発火しない", async () => {
    const wrapper = mount(ChipMultiSelect, {
      props: { modelValue: ["GROWTH", "STABILITY", "FREEDOM"], choices, max: 3, labelledBy: "q1" },
    });

    const unselected = wrapper.findAll(".chip-multi-select__chip")[3];
    expect(unselected?.attributes("disabled")).toBeDefined();

    await unselected?.trigger("click");

    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });

  it("上限に達していても選択済みのチップは外せる", async () => {
    const wrapper = mount(ChipMultiSelect, {
      props: { modelValue: ["GROWTH", "STABILITY", "FREEDOM"], choices, max: 3, labelledBy: "q1" },
    });

    await wrapper.findAll(".chip-multi-select__chip")[0]?.trigger("click");

    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([["STABILITY", "FREEDOM"]]);
  });
});
