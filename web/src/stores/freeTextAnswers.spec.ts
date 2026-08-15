import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useFreeTextAnswersStore, type FreeTextAnswer } from "./freeTextAnswers";

describe("freeTextAnswers store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("初期状態は空", () => {
    const store = useFreeTextAnswersStore();
    expect(store.answers).toEqual([]);
  });

  it("setAnswersで置き換え、resetで空にする", () => {
    const store = useFreeTextAnswersStore();
    const answers: FreeTextAnswer[] = [
      {
        area: "CAREER",
        slot: "SATISFIED",
        target_item_code: "CAREER_FULFILLMENT",
        generated_question: "Careerの中では…",
        body: "今の会社で任される範囲が広がってきた",
      },
    ];

    store.setAnswers(answers);
    expect(store.answers).toEqual(answers);

    store.reset();
    expect(store.answers).toEqual([]);
  });
});
