import { defineStore } from "pinia";
import type { ReflectionResult } from "../api/reflections";

/**
 * S-62が取得したWeekly Reflectionの結果一式をS-63へ引き渡す
 * (S-15→S-16の`assessmentResult`と同じ考え方。URLではなくクライアント側の状態で渡す)。
 */
export const useReflectionResultStore = defineStore("reflectionResult", {
  state: () => ({
    result: null as ReflectionResult | null,
  }),
  actions: {
    setResult(result: ReflectionResult): void {
      this.result = result;
    },
    reset(): void {
      this.result = null;
    },
  },
});
