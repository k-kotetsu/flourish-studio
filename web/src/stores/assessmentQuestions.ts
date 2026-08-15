import { defineStore } from "pinia";
import type { AssessmentQuestion } from "../api/assessmentQuestions";

/**
 * S-13で生成した自由記述8問をクライアント側に保持する(S-12の回答と同じく保存しない、クライアント保持のみ)。
 * S-14(P2-7、未実装)がこのストアを消費する想定。
 */
export const useAssessmentQuestionsStore = defineStore("assessmentQuestions", {
  state: () => ({
    questions: [] as AssessmentQuestion[],
  }),
  actions: {
    setQuestions(questions: AssessmentQuestion[]): void {
      this.questions = questions;
    },
    reset(): void {
      this.questions = [];
    },
  },
});
