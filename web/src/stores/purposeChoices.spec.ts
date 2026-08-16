import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { usePurposeChoicesStore } from "./purposeChoices";

describe("usePurposeChoicesStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("初期状態は空", () => {
    const store = usePurposeChoicesStore();

    expect(store.values).toEqual([]);
    expect(store.fulfillingMoments).toEqual([]);
    expect(store.idealDailyLife).toBeNull();
  });

  it("setAnswersで3問分の回答が記録される", () => {
    const store = usePurposeChoicesStore();

    store.setAnswers({
      values: ["GROWTH", "FREEDOM"],
      fulfillingMoments: ["HELPED_SOMEONE"],
      idealDailyLife: "HAVING_OPTIONS",
    });

    expect(store.values).toEqual(["GROWTH", "FREEDOM"]);
    expect(store.fulfillingMoments).toEqual(["HELPED_SOMEONE"]);
    expect(store.idealDailyLife).toBe("HAVING_OPTIONS");
  });

  it("resetで空に戻る", () => {
    const store = usePurposeChoicesStore();
    store.setAnswers({
      values: ["GROWTH"],
      fulfillingMoments: ["HELPED_SOMEONE"],
      idealDailyLife: "HAVING_OPTIONS",
    });

    store.reset();

    expect(store.values).toEqual([]);
    expect(store.fulfillingMoments).toEqual([]);
    expect(store.idealDailyLife).toBeNull();
  });

  it("asChoicesがPOST /ai/purpose-dialogue・purpose-proposals共通のchoices形式を返す", () => {
    const store = usePurposeChoicesStore();
    store.setAnswers({
      values: ["GROWTH", "FREEDOM"],
      fulfillingMoments: ["HELPED_SOMEONE"],
      idealDailyLife: "HAVING_OPTIONS",
    });

    expect(store.asChoices).toEqual([
      { question_code: "Q1", option_codes: ["GROWTH", "FREEDOM"] },
      { question_code: "Q2", option_codes: ["HELPED_SOMEONE"] },
      { question_code: "Q3", option_codes: ["HAVING_OPTIONS"] },
    ]);
  });

  it("asChoicesはidealDailyLife未選択のときQ3を空配列にする", () => {
    const store = usePurposeChoicesStore();

    expect(store.asChoices[2]).toEqual({ question_code: "Q3", option_codes: [] });
  });
});
