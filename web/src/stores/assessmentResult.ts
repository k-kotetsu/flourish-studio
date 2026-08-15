import { defineStore } from "pinia";
import type { AssessmentResult } from "../api/assessments";

/**
 * S-15が取得した現在地レポートの結果一式をS-16へ引き渡す(09_API設計3章の考え方に沿い、
 * URLではなくクライアント側の状態で渡す。S-14→S-15の`freeTextAnswers`と同じ扱い)。
 */
export const useAssessmentResultStore = defineStore("assessmentResult", {
  state: () => ({
    result: null as AssessmentResult | null,
  }),
  actions: {
    setResult(result: AssessmentResult): void {
      this.result = result;
    },
    reset(): void {
      this.result = null;
    },
  },
});
