import { defineStore } from "pinia";
import { COMMITMENT, SATISFACTION, type Area } from "../domain/questions";

/**
 * S-12(選択式24問)の回答をクライアント側に保持する(09_API設計3章「S-12の入力はクライアントが保持する」)。
 * サーバーには送らない。S-13(P2-6、未実装)で `POST /ai/assessment-questions` を呼ぶときに
 * `scale_answers` としてそのまま送信できる形(09_API設計5.2)で持つ。
 */
export interface ScaleAnswer {
  area: Area;
  question_kind: typeof SATISFACTION | typeof COMMITMENT;
  item_code?: string;
  score: number;
}

export const useAssessmentAnswersStore = defineStore("assessmentAnswers", {
  state: () => ({
    scaleAnswers: [] as ScaleAnswer[],
  }),
  actions: {
    /** 1領域分(6件)の回答をまとめて記録する。同じ領域を再度渡した場合は置き換える。 */
    recordArea(area: Area, answers: ScaleAnswer[]): void {
      this.scaleAnswers = [...this.scaleAnswers.filter((a) => a.area !== area), ...answers];
    },
    /** 「× 中断」→「やめる」で呼ぶ。未確定の回答はすべて破棄する。 */
    reset(): void {
      this.scaleAnswers = [];
    },
  },
});
