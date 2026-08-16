import { defineStore } from "pinia";

/**
 * S-31(選択式3問)の回答をクライアント側に保持する(04_画面設計 screen-list.md S-31「保存: しない」)。
 * S-32(AI対話、未実装)がこの内容をもとに対話する想定だが、S-32の入出力仕様は本タスクの参照範囲外のため
 * ここでは選択されたcode(domain/purposeChoices.ts)をそのまま持つだけにとどめる。
 */
export const usePurposeChoicesStore = defineStore("purposeChoices", {
  state: () => ({
    values: [] as string[],
    fulfillingMoments: [] as string[],
    idealDailyLife: null as string | null,
  }),
  actions: {
    setAnswers(answers: { values: string[]; fulfillingMoments: string[]; idealDailyLife: string }): void {
      this.values = answers.values;
      this.fulfillingMoments = answers.fulfillingMoments;
      this.idealDailyLife = answers.idealDailyLife;
    },
    reset(): void {
      this.values = [];
      this.fulfillingMoments = [];
      this.idealDailyLife = null;
    },
  },
});
