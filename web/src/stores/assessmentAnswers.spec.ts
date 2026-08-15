import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useAssessmentAnswersStore, type ScaleAnswer } from "./assessmentAnswers";

function careerAnswers(): ScaleAnswer[] {
  return [
    { area: "CAREER", question_kind: "SATISFACTION", item_code: "CAREER_FULFILLMENT", score: 4 },
    { area: "CAREER", question_kind: "COMMITMENT", score: 3 },
  ];
}

function financialAnswers(): ScaleAnswer[] {
  return [
    { area: "FINANCIAL", question_kind: "SATISFACTION", item_code: "FINANCIAL_SAVINGS", score: 1 },
    { area: "FINANCIAL", question_kind: "COMMITMENT", score: 0 },
  ];
}

describe("useAssessmentAnswersStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("初期状態は空", () => {
    const store = useAssessmentAnswersStore();
    expect(store.scaleAnswers).toEqual([]);
  });

  it("recordAreaで回答が積み上がり、他領域の回答は残る", () => {
    const store = useAssessmentAnswersStore();

    store.recordArea("CAREER", careerAnswers());
    store.recordArea("FINANCIAL", financialAnswers());

    expect(store.scaleAnswers).toHaveLength(4);
    expect(store.scaleAnswers).toEqual(expect.arrayContaining([...careerAnswers(), ...financialAnswers()]));
  });

  it("同じ領域を再度recordAreaすると、その領域だけ置き換わる", () => {
    const store = useAssessmentAnswersStore();
    store.recordArea("CAREER", careerAnswers());
    store.recordArea("FINANCIAL", financialAnswers());

    const updatedCareer: ScaleAnswer[] = [
      { area: "CAREER", question_kind: "SATISFACTION", item_code: "CAREER_FULFILLMENT", score: 0 },
      { area: "CAREER", question_kind: "COMMITMENT", score: 0 },
    ];
    store.recordArea("CAREER", updatedCareer);

    expect(store.scaleAnswers).toHaveLength(4);
    expect(store.scaleAnswers).toEqual(expect.arrayContaining([...updatedCareer, ...financialAnswers()]));
  });

  it("resetで空になる", () => {
    const store = useAssessmentAnswersStore();
    store.recordArea("CAREER", careerAnswers());

    store.reset();

    expect(store.scaleAnswers).toEqual([]);
  });
});
