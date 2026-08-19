import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import S14View from "./S-14.vue";
import type { AssessmentQuestion } from "../api/assessmentQuestions";
import { useAssessmentQuestionsStore } from "../stores/assessmentQuestions";
import { useFreeTextAnswersStore } from "../stores/freeTextAnswers";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
}));

function full8Questions(): AssessmentQuestion[] {
  const questions: AssessmentQuestion[] = [];
  for (const area of ["CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL"] as const) {
    questions.push({
      area,
      slot: "SATISFIED",
      target_item_code: `${area}_HIGH`,
      text: `${area}の中では「最も高い項目」が満たされているようですね。`,
    });
    questions.push({
      area,
      slot: "CONCERN",
      target_item_code: `${area}_LOW`,
      text: `一方で「${area}の最も低い項目」は気になっているようですね。`,
    });
  }
  return questions;
}

afterEach(() => {
  push.mockReset();
  replace.mockReset();
});

describe("S-14", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("8問揃っていなければS-11へ差し戻す", () => {
    mount(S14View);

    expect(replace).toHaveBeenCalledWith("/s-11");
  });

  it("8問を領域ごとに満たされている問い→気になっている問いの順で表示する", () => {
    const questionsStore = useAssessmentQuestionsStore();
    questionsStore.setQuestions(full8Questions());

    const wrapper = mount(S14View);

    expect(replace).not.toHaveBeenCalled();
    const labels = wrapper.findAll(".s14__question-text").map((el) => el.text());
    expect(labels).toHaveLength(8);
    expect(labels[0]).toContain("CAREERの中では");
    expect(labels[1]).toContain("CAREERの最も低い項目");
    expect(labels[6]).toContain("SOCIALの中では");
    expect(labels[7]).toContain("SOCIALの最も低い項目");
    // P7-3: 4領域アイコンを見出しごとに表示する
    expect(wrapper.findAll(".s14__heading svg")).toHaveLength(4);
  });

  it("textareaに1,000文字の上限が設定されている", () => {
    const questionsStore = useAssessmentQuestionsStore();
    questionsStore.setQuestions(full8Questions());

    const wrapper = mount(S14View);

    const textarea = wrapper.find("textarea");
    expect(textarea.attributes("maxlength")).toBe("1000");
  });

  it("全問空欄のまま「レポートを作る」でS-15へ進める", async () => {
    const questionsStore = useAssessmentQuestionsStore();
    questionsStore.setQuestions(full8Questions());

    const wrapper = mount(S14View);
    await wrapper.find(".s14__cta button").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-15");
    const freeTextStore = useFreeTextAnswersStore();
    expect(freeTextStore.answers).toHaveLength(8);
    expect(freeTextStore.answers.every((a) => a.body === "")).toBe(true);
  });

  it("入力した内容をgenerated_questionと一緒にストアへ保存する", async () => {
    const questionsStore = useAssessmentQuestionsStore();
    questionsStore.setQuestions(full8Questions());

    const wrapper = mount(S14View);
    const textareas = wrapper.findAll("textarea");
    await textareas[0]?.setValue("いま任される範囲が広がってきた");

    await wrapper.find(".s14__cta button").trigger("click");

    const freeTextStore = useFreeTextAnswersStore();
    const careerSatisfied = freeTextStore.answers.find(
      (a) => a.area === "CAREER" && a.slot === "SATISFIED",
    );
    expect(careerSatisfied?.body).toBe("いま任される範囲が広がってきた");
    expect(careerSatisfied?.generated_question).toBe(
      "CAREERの中では「最も高い項目」が満たされているようですね。",
    );
  });

  it("「戻る」でS-13を経由せずS-12(Social)へ直接戻す", async () => {
    const questionsStore = useAssessmentQuestionsStore();
    questionsStore.setQuestions(full8Questions());

    const wrapper = mount(S14View);
    await wrapper.find(".app-header-flow__nav").trigger("click");

    expect(push).toHaveBeenCalledWith("/s-12/social");
  });
});
