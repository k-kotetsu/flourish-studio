import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import type { AssessmentResult } from "../api/assessments";
import { useAssessmentResultStore } from "./assessmentResult";

function result(): AssessmentResult {
  return {
    nickname: "全速前進、燃料計は未確認",
    articulation_stage: "SPROUT",
    commitment_stage: "SEED",
    commitment_score: 3,
    safety_flag: false,
    areas: [],
    generated_at: "2026-08-08T04:12:00Z",
  };
}

describe("useAssessmentResultStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("初期状態はnull", () => {
    const store = useAssessmentResultStore();
    expect(store.result).toBeNull();
  });

  it("setResultで保持する", () => {
    const store = useAssessmentResultStore();
    store.setResult(result());
    expect(store.result).toEqual(result());
  });

  it("resetでnullに戻る", () => {
    const store = useAssessmentResultStore();
    store.setResult(result());
    store.reset();
    expect(store.result).toBeNull();
  });
});
