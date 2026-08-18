import { defineStore } from "pinia";

/**
 * S-61(Weekly Reflection：回答)の回答をクライアント側に保持する(スキルflourish-api
 * 「入力途中を送らない」。S-61もS-14などと同じく、送信ボタンを押すまでサーバに送らない)。
 * `POST /reflections`(09_API設計5.14、P5-2で実装)の`statuses`/`note`にそのまま渡せる形で持つ。
 * ステータスの3値は`08_データモデル`5.1(`ReflectionStatus`)に合わせる。
 */
export type ReflectionStatus = "ON_TRACK" | "STALLED" | "REVISE";

export interface ReflectionStatusAnswer {
  goal_key: string;
  status: ReflectionStatus;
}

export const useReflectionAnswersStore = defineStore("reflectionAnswers", {
  state: () => ({
    statuses: [] as ReflectionStatusAnswer[],
    note: null as string | null,
  }),
  actions: {
    setAnswers(answers: { statuses: ReflectionStatusAnswer[]; note: string | null }): void {
      this.statuses = answers.statuses;
      this.note = answers.note;
    },
    reset(): void {
      this.statuses = [];
      this.note = null;
    },
  },
});
