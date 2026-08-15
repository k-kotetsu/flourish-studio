import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import type { AssessmentQuestion } from "../api/assessmentQuestions";
import { useAssessmentQuestionsStore } from "./assessmentQuestions";

function questions(): AssessmentQuestion[] {
  return [
    { area: "CAREER", slot: "SATISFIED", target_item_code: "CAREER_FULFILLMENT", text: "..." },
    { area: "CAREER", slot: "CONCERN", target_item_code: "CAREER_COMPENSATION", text: "..." },
  ];
}

describe("useAssessmentQuestionsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("初期状態は空", () => {
    const store = useAssessmentQuestionsStore();
    expect(store.questions).toEqual([]);
  });

  it("setQuestionsで保持する", () => {
    const store = useAssessmentQuestionsStore();
    store.setQuestions(questions());
    expect(store.questions).toEqual(questions());
  });

  it("resetで空になる", () => {
    const store = useAssessmentQuestionsStore();
    store.setQuestions(questions());
    store.reset();
    expect(store.questions).toEqual([]);
  });
});
