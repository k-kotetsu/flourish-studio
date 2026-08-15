import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import S15View from "./S-15.vue";
import { generateAssessmentReport } from "../api/assessments";
import { useAssessmentAnswersStore, type ScaleAnswer } from "../stores/assessmentAnswers";
import { useAssessmentResultStore } from "../stores/assessmentResult";
import { useFreeTextAnswersStore, type FreeTextAnswer } from "../stores/freeTextAnswers";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, replace }),
}));
vi.mock("../api/assessments", () => ({
  generateAssessmentReport: vi.fn(),
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

function full8FreeTextAnswers(): FreeTextAnswer[] {
  const answers: FreeTextAnswer[] = [];
  for (const area of ["CAREER", "FINANCIAL", "PHYSICAL", "SOCIAL"] as const) {
    for (const slot of ["SATISFIED", "CONCERN"] as const) {
      answers.push({ area, slot, target_item_code: `${area}_0`, generated_question: "...", body: "" });
    }
  }
  return answers;
}

const resultBody = {
  nickname: "全速前進、燃料計は未確認",
  articulation_stage: "SPROUT" as const,
  commitment_stage: "SEED" as const,
  commitment_score: 3,
  safety_flag: false,
  areas: [],
  generated_at: "2026-08-08T04:12:00Z",
};

afterEach(() => {
  push.mockReset();
  replace.mockReset();
  vi.mocked(generateAssessmentReport).mockReset();
});

describe("S-15", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("選択式24件・自由記述8件が揃っていなければS-11へ差し戻す", async () => {
    const answersStore = useAssessmentAnswersStore();
    answersStore.recordArea("CAREER", [{ area: "CAREER", question_kind: "COMMITMENT", score: 3 }]);

    mount(S15View);
    await flushPromises();

    expect(replace).toHaveBeenCalledWith("/s-11");
    expect(generateAssessmentReport).not.toHaveBeenCalled();
  });

  it("画面到達時にレポート生成を呼び、成功したら結果を保存してS-16へ遷移する", async () => {
    const answersStore = useAssessmentAnswersStore();
    answersStore.recordArea("CAREER", full24Answers());
    const freeTextStore = useFreeTextAnswersStore();
    freeTextStore.setAnswers(full8FreeTextAnswers());
    vi.mocked(generateAssessmentReport).mockResolvedValue(resultBody);

    mount(S15View);
    await flushPromises();

    expect(generateAssessmentReport).toHaveBeenCalledOnce();
    expect(push).toHaveBeenCalledWith("/s-16");
    const resultStore = useAssessmentResultStore();
    expect(resultStore.result).toEqual(resultBody);
  });

  it("失敗したら同じ画面の中身がエラー表示に入れ替わる(別画面へ遷移しない)", async () => {
    const answersStore = useAssessmentAnswersStore();
    answersStore.recordArea("CAREER", full24Answers());
    const freeTextStore = useFreeTextAnswersStore();
    freeTextStore.setAnswers(full8FreeTextAnswers());
    vi.mocked(generateAssessmentReport).mockRejectedValueOnce(new Error("provider error"));

    const wrapper = mount(S15View);
    await flushPromises();

    expect(push).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("うまくレポートを作れませんでした");
    expect(wrapper.text()).toContain("書いていただいた内容は、ちゃんと残っています");
  });

  it("「もう一度生成する」を押したときだけ再試行する(自動リトライしない)", async () => {
    const answersStore = useAssessmentAnswersStore();
    answersStore.recordArea("CAREER", full24Answers());
    const freeTextStore = useFreeTextAnswersStore();
    freeTextStore.setAnswers(full8FreeTextAnswers());
    vi.mocked(generateAssessmentReport).mockRejectedValueOnce(new Error("provider error"));
    vi.mocked(generateAssessmentReport).mockResolvedValueOnce(resultBody);

    const wrapper = mount(S15View);
    await flushPromises();
    expect(generateAssessmentReport).toHaveBeenCalledOnce();

    await wrapper.find("button").trigger("click");
    await flushPromises();

    expect(generateAssessmentReport).toHaveBeenCalledTimes(2);
    expect(push).toHaveBeenCalledWith("/s-16");
  });

  it("「回答に戻る」でS-14へ戻す", async () => {
    const answersStore = useAssessmentAnswersStore();
    answersStore.recordArea("CAREER", full24Answers());
    const freeTextStore = useFreeTextAnswersStore();
    freeTextStore.setAnswers(full8FreeTextAnswers());
    vi.mocked(generateAssessmentReport).mockRejectedValueOnce(new Error("provider error"));

    const wrapper = mount(S15View);
    await flushPromises();

    const buttons = wrapper.findAll("button");
    await buttons[buttons.length - 1]?.trigger("click");

    expect(push).toHaveBeenCalledWith("/s-14");
  });
});
