import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import S16View from "./S-16.vue";
import type { AssessmentResult } from "../api/assessments";
import { useAssessmentResultStore } from "../stores/assessmentResult";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
}));

function result(): AssessmentResult {
  return {
    nickname: "全速前進、燃料計は未確認",
    articulation_stage: "SPROUT",
    commitment_stage: "SEEDLING",
    commitment_score: 8,
    safety_flag: false,
    areas: [
      {
        area: "SOCIAL",
        satisfied_text: "Socialの満たされている点。",
        concern_text: "Socialの気になっている点。",
        advice_text: "Socialのこれからできそうなこと。",
      },
      {
        area: "CAREER",
        satisfied_text: "Careerの満たされている点。",
        concern_text: "Careerの気になっている点。",
        advice_text: "Careerのこれからできそうなこと。",
      },
      {
        area: "FINANCIAL",
        satisfied_text: "Financialの満たされている点。",
        concern_text: "Financialの気になっている点。",
        advice_text: "Financialのこれからできそうなこと。",
      },
      {
        area: "PHYSICAL",
        satisfied_text: "Physicalの満たされている点。",
        concern_text: "Physicalの気になっている点。",
        advice_text: "Physicalのこれからできそうなこと。",
      },
    ],
    generated_at: "2026-08-08T04:12:00Z",
  };
}

afterEach(() => {
  push.mockReset();
  replace.mockReset();
});

describe("S-16", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("結果を持たずに開かれたらS-11へ差し戻す", () => {
    mount(S16View);

    expect(replace).toHaveBeenCalledWith("/s-11");
  });

  it("あだ名と免責の一文を表示する", () => {
    useAssessmentResultStore().setResult(result());

    const wrapper = mount(S16View);

    expect(wrapper.text()).toContain("全速前進、燃料計は未確認");
    expect(wrapper.text()).toContain("これがあなたを表すものではありません");
  });

  it("4領域をCareer→Financial→Physical→Socialの順で、3ブロックとも表示する", () => {
    useAssessmentResultStore().setResult(result());

    const wrapper = mount(S16View);

    const headings = wrapper.findAll(".s16__area-en").map((el) => el.text());
    expect(headings).toEqual(["Career", "Financial", "Physical", "Social"]);
    expect(wrapper.text()).toContain("Careerの満たされている点。");
    expect(wrapper.text()).toContain("Careerの気になっている点。");
    expect(wrapper.text()).toContain("Careerのこれからできそうなこと。");
  });

  it("言語化度・コミット度は4段階すべてを表示し、該当段階のみ点灯する。数値は出さない", () => {
    useAssessmentResultStore().setResult(result());

    const wrapper = mount(S16View);

    const stageGroups = wrapper.findAll(".growth-stage-display__stages");
    expect(stageGroups).toHaveLength(2);

    const articulationStages = stageGroups[0]!.findAll(".growth-stage-display__stage");
    expect(articulationStages.map((el) => el.text())).toEqual(["種", "芽", "苗", "木"]);
    expect(articulationStages[1]!.classes()).toContain("growth-stage-display__stage--lit"); // SPROUT = 芽
    expect(articulationStages[0]!.classes()).not.toContain("growth-stage-display__stage--lit");
    expect(articulationStages[2]!.classes()).not.toContain("growth-stage-display__stage--lit");
    expect(articulationStages[3]!.classes()).not.toContain("growth-stage-display__stage--lit");

    const commitmentStages = stageGroups[1]!.findAll(".growth-stage-display__stage");
    expect(commitmentStages[2]!.classes()).toContain("growth-stage-display__stage--lit"); // SEEDLING = 苗

    expect(wrapper.text()).not.toContain("8"); // commitment_scoreを出さない
  });

  it("「ありたい姿を作る」でS-21へ遷移する", async () => {
    useAssessmentResultStore().setResult(result());

    const wrapper = mount(S16View);
    await wrapper.find("button").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-21");
  });

  it("safety_flagが立っていたら評価(あだ名・4領域・言語化度)を表示しない", () => {
    useAssessmentResultStore().setResult({ ...result(), safety_flag: true });

    const wrapper = mount(S16View);

    expect(wrapper.find(".s16__nickname").exists()).toBe(false);
    expect(wrapper.find(".s16__area-en").exists()).toBe(false);
    expect(wrapper.find(".growth-stage-display__stages").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("全速前進、燃料計は未確認");
    expect(wrapper.find('[data-testid="safety-notice"]').exists()).toBe(true);
  });
});
