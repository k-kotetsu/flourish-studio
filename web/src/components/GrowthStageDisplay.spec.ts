import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import GrowthStageDisplay from "./GrowthStageDisplay.vue";

describe("GrowthStageDisplay", () => {
  it("種・芽・苗・木の4段階すべてを表示する", () => {
    const wrapper = mount(GrowthStageDisplay, {
      props: {
        axisName: "言語化度",
        axisDescription: "自分の考えが、どのくらい自分の言葉になっているか",
        stage: "SPROUT",
      },
    });

    const stages = wrapper.findAll(".growth-stage-display__stage");
    expect(stages.map((el) => el.text())).toEqual(["種", "芽", "苗", "木"]);
  });

  it("該当する現在地だけを点灯する。数値は出さない", () => {
    const wrapper = mount(GrowthStageDisplay, {
      props: {
        axisName: "コミット度",
        axisDescription: "考えていることを、どのくらい行動につなげられているか",
        stage: "SEEDLING",
      },
    });

    const stages = wrapper.findAll(".growth-stage-display__stage");
    expect(stages[0]!.classes()).not.toContain("growth-stage-display__stage--lit"); // 種
    expect(stages[1]!.classes()).not.toContain("growth-stage-display__stage--lit"); // 芽
    expect(stages[2]!.classes()).toContain("growth-stage-display__stage--lit"); // 苗
    expect(stages[3]!.classes()).not.toContain("growth-stage-display__stage--lit"); // 木

    expect(wrapper.text()).not.toMatch(/\d/);
  });

  it("軸名と軸の説明を表示する", () => {
    const wrapper = mount(GrowthStageDisplay, {
      props: {
        axisName: "言語化度",
        axisDescription: "自分の考えが、どのくらい自分の言葉になっているか",
        stage: "SEED",
      },
    });

    expect(wrapper.text()).toContain("言語化度");
    expect(wrapper.text()).toContain("自分の考えが、どのくらい自分の言葉になっているか");
  });

  it("role=imgとaria-labelで現在地を伝える", () => {
    const wrapper = mount(GrowthStageDisplay, {
      props: {
        axisName: "言語化度",
        axisDescription: "自分の考えが、どのくらい自分の言葉になっているか",
        stage: "TREE",
      },
    });

    const region = wrapper.find(".growth-stage-display__stages");
    expect(region.attributes("role")).toBe("img");
    expect(region.attributes("aria-label")).toBe("言語化度: 木");
  });

  it("線画アイコンをインラインSVGで4段階分描く", () => {
    const wrapper = mount(GrowthStageDisplay, {
      props: {
        axisName: "言語化度",
        axisDescription: "自分の考えが、どのくらい自分の言葉になっているか",
        stage: "SEED",
      },
    });

    expect(wrapper.findAll(".growth-stage-display__icon")).toHaveLength(4);
  });
});
