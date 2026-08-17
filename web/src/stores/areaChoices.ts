import { defineStore } from "pinia";
import type { AreaDialogueChoice } from "../api/areaDialogue";
import type { Area } from "../domain/questions";

/**
 * S-51(領域：選択式質問)の回答をクライアント側に保持する(04_画面設計 screen-list.md S-51「保存: しない」)。
 * S-52(AI対話、P4-3)・S-53(3案生成、P4-4)がこの内容をもとにAIを呼ぶ想定。
 * ありたい姿(purposeChoices)と異なり、この画面は一度に1領域分だけを扱う
 * (`03_ユーザーフロー`・`06_ワイヤーフレーム`とも「領域作成」は1領域ずつ進むフロー)。
 */
export const useAreaChoicesStore = defineStore("areaChoices", {
  state: () => ({
    area: null as Area | null,
    changeItemCode: null as string | null,
    values: [] as string[],
    positions: [] as string[],
  }),
  getters: {
    // S-52(P4-3)・S-53(P4-4)の両方がこの形を要求する(`POST /ai/area-dialogue`のchoices)。
    // purposeChoicesストアのasChoicesと同じ考え方でストア側に置き、呼び出し側で組み立てない。
    asChoices: (state): AreaDialogueChoice[] => [
      { question_code: "Q1", option_codes: state.changeItemCode ? [state.changeItemCode] : [] },
      { question_code: "Q2", option_codes: state.values },
      { question_code: "Q3", option_codes: state.positions },
    ],
  },
  actions: {
    setAnswers(answers: { area: Area; changeItemCode: string; values: string[]; positions: string[] }): void {
      this.area = answers.area;
      this.changeItemCode = answers.changeItemCode;
      this.values = answers.values;
      this.positions = answers.positions;
    },
    reset(): void {
      this.area = null;
      this.changeItemCode = null;
      this.values = [];
      this.positions = [];
    },
  },
});
