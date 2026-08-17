import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useAreaChoicesStore } from "./areaChoices";

describe("useAreaChoicesStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("初期状態は空", () => {
    const store = useAreaChoicesStore();

    expect(store.area).toBeNull();
    expect(store.changeItemCode).toBeNull();
    expect(store.values).toEqual([]);
    expect(store.positions).toEqual([]);
  });

  it("setAnswersで1領域分の回答が記録される", () => {
    const store = useAreaChoicesStore();

    store.setAnswers({
      area: "CAREER",
      changeItemCode: "CAREER_OUTLOOK",
      values: ["CAREER_VALUE_GROWTH"],
      positions: ["CAREER_POSITION_GROWTH"],
    });

    expect(store.area).toBe("CAREER");
    expect(store.changeItemCode).toBe("CAREER_OUTLOOK");
    expect(store.values).toEqual(["CAREER_VALUE_GROWTH"]);
    expect(store.positions).toEqual(["CAREER_POSITION_GROWTH"]);
  });

  it("resetで空に戻る", () => {
    const store = useAreaChoicesStore();
    store.setAnswers({
      area: "CAREER",
      changeItemCode: "CAREER_OUTLOOK",
      values: ["CAREER_VALUE_GROWTH"],
      positions: ["CAREER_POSITION_GROWTH"],
    });

    store.reset();

    expect(store.area).toBeNull();
    expect(store.changeItemCode).toBeNull();
    expect(store.values).toEqual([]);
    expect(store.positions).toEqual([]);
  });

  it("asChoicesがPOST /ai/area-dialogueのchoices形式を返す", () => {
    const store = useAreaChoicesStore();
    store.setAnswers({
      area: "CAREER",
      changeItemCode: "CAREER_OUTLOOK",
      values: ["CAREER_VALUE_GROWTH", "CAREER_VALUE_AUTONOMY"],
      positions: ["CAREER_POSITION_GROWTH"],
    });

    expect(store.asChoices).toEqual([
      { question_code: "Q1", option_codes: ["CAREER_OUTLOOK"] },
      { question_code: "Q2", option_codes: ["CAREER_VALUE_GROWTH", "CAREER_VALUE_AUTONOMY"] },
      { question_code: "Q3", option_codes: ["CAREER_POSITION_GROWTH"] },
    ]);
  });

  it("asChoicesはchangeItemCode未選択のときQ1を空配列にする", () => {
    const store = useAreaChoicesStore();

    expect(store.asChoices[0]).toEqual({ question_code: "Q1", option_codes: [] });
  });
});
