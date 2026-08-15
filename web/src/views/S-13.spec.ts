import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import S13View from "./S-13.vue";
import { generateAssessmentQuestions } from "../api/assessmentQuestions";
import { useAssessmentAnswersStore, type ScaleAnswer } from "../stores/assessmentAnswers";
import { useAssessmentQuestionsStore } from "../stores/assessmentQuestions";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
}));
vi.mock("../api/assessmentQuestions", () => ({
  generateAssessmentQuestions: vi.fn(),
}));

function full24Answers(): ScaleAnswer[] {
  const answers: ScaleAnswer[] = [];
  for (const area of ["CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL"] as const) {
    for (let i = 0; i < 5; i += 1) {
      answers.push({ area, question_kind: "SATISFACTION", item_code: `${area}_${i}`, score: 3 });
    }
    answers.push({ area, question_kind: "COMMITMENT", score: 3 });
  }
  return answers;
}

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  vi.mocked(generateAssessmentQuestions).mockReset();
});

describe("S-13", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("24件揃っていなければS-11へ差し戻す", async () => {
    const answersStore = useAssessmentAnswersStore();
    answersStore.recordArea("CAREER", [{ area: "CAREER", question_kind: "COMMITMENT", score: 3 }]);

    mount(S13View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-11");
    expect(generateAssessmentQuestions).not.toHaveBeenCalled();
  });

  it("画面到達時に問い生成を呼び、成功したら結果を保存してS-14へ遷移する", async () => {
    const answersStore = useAssessmentAnswersStore();
    answersStore.recordArea("CAREER", full24Answers());
    const generated = [
      { area: "CAREER" as const, slot: "SATISFIED" as const, target_item_code: "CAREER_0", text: "..." },
    ];
    vi.mocked(generateAssessmentQuestions).mockResolvedValue(generated);

    mount(S13View);
    await flushPromises();

    expect(generateAssessmentQuestions).toHaveBeenCalledOnce();
    expect(push).toHaveBeenCalledWith("/s-14");
    const questionsStore = useAssessmentQuestionsStore();
    expect(questionsStore.questions).toEqual(generated);
  });

  it("失敗したら同じ画面の中身がエラー表示に入れ替わる(別画面へ遷移しない)", async () => {
    const answersStore = useAssessmentAnswersStore();
    answersStore.recordArea("CAREER", full24Answers());
    vi.mocked(generateAssessmentQuestions).mockRejectedValueOnce(new Error("provider error"));

    const wrapper = mount(S13View);
    await flushPromises();

    expect(push).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("うまく読み取れませんでした");
    expect(wrapper.text()).toContain("選んでいただいた内容は、ちゃんと残っています");
  });

  it("「もう一度生成する」を押したときだけ再試行する(自動リトライしない)", async () => {
    const answersStore = useAssessmentAnswersStore();
    answersStore.recordArea("CAREER", full24Answers());
    const generated = [
      { area: "CAREER" as const, slot: "SATISFIED" as const, target_item_code: "CAREER_0", text: "..." },
    ];
    vi.mocked(generateAssessmentQuestions).mockRejectedValueOnce(new Error("provider error"));
    vi.mocked(generateAssessmentQuestions).mockResolvedValueOnce(generated);

    const wrapper = mount(S13View);
    await flushPromises();
    expect(generateAssessmentQuestions).toHaveBeenCalledOnce();

    await wrapper.find("button").trigger("click");
    await flushPromises();

    expect(generateAssessmentQuestions).toHaveBeenCalledTimes(2);
    expect(push).toHaveBeenCalledWith("/s-14");
  });

  it("「回答に戻る」でS-12(Social)へ戻す", async () => {
    const answersStore = useAssessmentAnswersStore();
    answersStore.recordArea("CAREER", full24Answers());
    vi.mocked(generateAssessmentQuestions).mockRejectedValueOnce(new Error("provider error"));

    const wrapper = mount(S13View);
    await flushPromises();

    const buttons = wrapper.findAll("button");
    await buttons[buttons.length - 1]?.trigger("click");

    expect(push).toHaveBeenCalledWith("/s-12/social");
  });
});
