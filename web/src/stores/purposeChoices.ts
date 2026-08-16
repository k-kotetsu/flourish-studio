import { defineStore } from "pinia";
import type { PurposeDialogueChoice } from "../api/purposeDialogue";

/**
 * S-31(選択式3問)の回答をクライアント側に保持する(04_画面設計 screen-list.md S-31「保存: しない」)。
 * S-32(AI対話)・S-33(3案生成、P3-7)がこの内容をもとにAIを呼ぶ。
 */
export const usePurposeChoicesStore = defineStore("purposeChoices", {
  state: () => ({
    values: [] as string[],
    fulfillingMoments: [] as string[],
    idealDailyLife: null as string | null,
  }),
  getters: {
    // POST /ai/purpose-dialogue・POST /ai/purpose-proposalsの両方が使う`choices`形式(09_API設計5.6)。
    asChoices: (state): PurposeDialogueChoice[] => [
      { question_code: "Q1", option_codes: state.values },
      { question_code: "Q2", option_codes: state.fulfillingMoments },
      {
        question_code: "Q3",
        option_codes: state.idealDailyLife ? [state.idealDailyLife] : [],
      },
    ],
  },
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
