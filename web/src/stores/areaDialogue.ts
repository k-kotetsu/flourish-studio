import { defineStore } from "pinia";
import type { AreaDialogueMessage } from "../api/areaDialogue";

/**
 * S-52(領域のAI対話)の対話履歴をクライアント側に保持する。対話履歴はサーバーに残さず、
 * リクエストのたびに全部送る(09_API設計3.2、purposeDialogueストアと同じ設計)。
 * 確定時(`POST /area-plans`、P4-6)にまとめて保存する想定で、それまではこのストアだけが
 * 対話全文を持つ。
 */
export const useAreaDialogueStore = defineStore("areaDialogue", {
  state: () => ({
    messages: [] as AreaDialogueMessage[],
    remaining: 2,
  }),
  getters: {
    // 2往復完了後も対話は続けられる(wireframe-spec.md、S-32と同じ考え方)。「理想の状態を作る」の出現条件のみに使う
    canCreateIdealState: (state) => state.remaining <= 0 && state.messages.length > 0,
  },
  actions: {
    addMessage(message: AreaDialogueMessage): void {
      this.messages.push(message);
    },
    setRemaining(remaining: number): void {
      this.remaining = remaining;
    },
    reset(): void {
      this.messages = [];
      this.remaining = 2;
    },
  },
});
