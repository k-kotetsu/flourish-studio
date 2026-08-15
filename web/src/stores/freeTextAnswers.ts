import { defineStore } from "pinia";
import type { QuestionSlot } from "../api/assessmentQuestions";
import type { Area } from "../domain/questions";

/**
 * S-14(自由記述8問)の回答をクライアント側に保持する(09_API設計3章「S-14の入力はクライアントが保持する」)。
 * `POST /assessments`(P2-8、未実装)の`free_text_answers`(09_API設計5.3)にそのまま渡せる形で持つ。
 */
export interface FreeTextAnswer {
  area: Area;
  slot: QuestionSlot;
  target_item_code: string;
  generated_question: string;
  body: string;
}

export const useFreeTextAnswersStore = defineStore("freeTextAnswers", {
  state: () => ({
    answers: [] as FreeTextAnswer[],
  }),
  actions: {
    setAnswers(answers: FreeTextAnswer[]): void {
      this.answers = answers;
    },
    reset(): void {
      this.answers = [];
    },
  },
});
