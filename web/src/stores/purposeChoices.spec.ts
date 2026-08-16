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
});
